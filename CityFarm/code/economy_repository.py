"""PostgreSQL transactions for durable player state and food inventory."""
import os
from pathlib import Path

import psycopg
from psycopg.rows import dict_row


class EconomyRepository:
    def __init__(self, database_url=None):
        self.database_url = database_url or os.environ["DATABASE_URL"]

    def connect(self):
        return psycopg.connect(self.database_url, row_factory=dict_row)

    def initialize_schema(self):
        with self.connect() as connection:
            connection.execute(Path(__file__).with_name("schema.sql").read_text())

    def initialize_player(self, owner, initial_energy, initial_soil_health):
        with self.connect() as connection:
            connection.execute("""
                INSERT INTO players (id, energy, soil_health) VALUES (%s, %s, %s)
                ON CONFLICT (id) DO NOTHING
            """, (owner, initial_energy, initial_soil_health))

    def load_player_resource_status(self, owner):
        with self.connect() as connection:
            return connection.execute(
                "SELECT coins, energy, soil_health FROM players WHERE id = %s",
                (owner,)).fetchone()

    def save_player_character(self, owner, name, role):
        with self.connect() as connection:
            connection.execute("""
                INSERT INTO players (id, name, role) VALUES (%s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name, role = EXCLUDED.role
            """, (owner, name, role))

    def load_character_summaries(self):
        with self.connect() as connection:
            return connection.execute("""
                SELECT id, name, role, food_produced, food_eaten,
                       coins_earned_work, coins_spent_soil
                FROM players WHERE role IS NOT NULL ORDER BY role, lower(name), id LIMIT 100
            """).fetchall()

    def count_available_food(self):
        with self.connect() as connection:
            return connection.execute(
                "SELECT coalesce(sum(quantity), 0)::bigint AS quantity FROM food_lots"
            ).fetchone()["quantity"]

    def is_challenge_finalized(self, challenge_id):
        with self.connect() as connection:
            return connection.execute(
                "SELECT 1 FROM challenge_results WHERE challenge_id = %s",
                (challenge_id,)).fetchone() is not None

    def finalize_challenge(self, challenges, raw, challenge_id, owner, kind,
                           cost=0, reward=0, cancelled=False):
        """Lock player; commit reward and replay protection before Redis cleanup."""
        with self.connect() as connection:
            player = connection.execute(
                "SELECT * FROM players WHERE id = %s FOR UPDATE", (owner,)).fetchone()
            if connection.execute(
                "SELECT 1 FROM challenge_results WHERE challenge_id = %s",
                (challenge_id,)).fetchone():
                return 0
            active_id, current = challenges.load_active_challenge(owner, kind)
            if active_id != challenge_id or current != raw:
                return 0
            resource = "soil_health" if kind == "farmer" else "energy"
            if not cancelled and player[resource] < cost:
                return -2
            if not cancelled and kind == "farmer":
                connection.execute("""
                    UPDATE players SET soil_health = soil_health - %s,
                        food_produced = food_produced + %s WHERE id = %s
                """, (cost, reward, owner))
                connection.execute(
                    "INSERT INTO food_lots (farmer_id, quantity) VALUES (%s, %s)",
                    (owner, reward))
            elif not cancelled:
                connection.execute("""
                    UPDATE players SET energy = energy - %s, coins = coins + %s,
                        coins_earned_work = coins_earned_work + %s WHERE id = %s
                """, (cost, reward, reward, owner))
            connection.execute("""
                INSERT INTO challenge_results (challenge_id, player_id, outcome)
                VALUES (%s, %s, %s)
            """, (challenge_id, owner, "cancelled" if cancelled else "completed"))
        challenges.clear_completed_challenge(owner, kind, challenge_id)
        return 1

    def restore_to_minimum(self, owner, resource, recovery):
        if resource not in ("energy", "soil_health"):
            raise ValueError("Unknown resource")
        with self.connect() as connection:
            row = connection.execute(psycopg.sql.SQL("""
                UPDATE players SET {resource} = %s
                WHERE id = %s AND {resource} < %s RETURNING {resource}
            """).format(resource=psycopg.sql.Identifier(resource)),
                (recovery, owner, recovery)).fetchone()
            return row[resource] if row else -1

    def pay_to_prepare_soil(self, owner, cost, maximum, recovery):
        with self.connect() as connection:
            player = connection.execute(
                "SELECT * FROM players WHERE id = %s FOR UPDATE", (owner,)).fetchone()
            if player["soil_health"] >= maximum:
                return -1
            if player["coins"] < cost:
                return -2
            renewed = min(maximum, player["soil_health"] + recovery)
            connection.execute("""
                UPDATE players SET coins = coins - %s, soil_health = %s,
                    coins_spent_soil = coins_spent_soil + %s WHERE id = %s
            """, (cost, renewed, cost, owner))
            return renewed

    def purchase_next_food(self, owner, price, maximum_energy, gained_energy):
        with self.connect() as connection:
            # Serialize FIFO purchases, then lock player rows in a stable order.
            connection.execute("SELECT pg_advisory_xact_lock(734821)")
            lot = connection.execute(
                "SELECT * FROM food_lots ORDER BY id LIMIT 1 FOR UPDATE").fetchone()
            farmer_id = lot["farmer_id"] if lot else owner
            rows = connection.execute(
                "SELECT * FROM players WHERE id = ANY(%s) ORDER BY id FOR UPDATE",
                ([owner, farmer_id],)).fetchall()
            player = next(row for row in rows if row["id"] == owner)
            if player["coins"] < price:
                return -1, ""
            if player["energy"] >= maximum_energy:
                return -2, ""
            if not lot:
                return -3, ""
            if lot["quantity"] == 1:
                connection.execute("DELETE FROM food_lots WHERE id = %s", (lot["id"],))
            else:
                connection.execute(
                    "UPDATE food_lots SET quantity = quantity - 1 WHERE id = %s",
                    (lot["id"],))
            connection.execute("""
                UPDATE players SET coins = coins - %s, energy = least(%s, energy + %s),
                    food_eaten = food_eaten + 1 WHERE id = %s
            """, (price, maximum_energy, gained_energy, owner))
            connection.execute("UPDATE players SET coins = coins + %s WHERE id = %s",
                               (price, farmer_id))
            connection.execute("""
                INSERT INTO food_purchases (citizen_id, farmer_id, price) VALUES (%s, %s, %s)
            """, (owner, farmer_id, price))
            return 1, farmer_id
