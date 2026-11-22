"""Economia Food com Redis DB 15 (não toca o DB 0 do jogo)."""
import json
import os
from pathlib import Path
import sys
import unittest
from concurrent.futures import ThreadPoolExecutor

import redis

CODE_DIRECTORY = Path("/code")
if not CODE_DIRECTORY.is_dir():
    CODE_DIRECTORY = Path(__file__).resolve().parents[1] / "CityFarm" / "code"
sys.path.insert(0, str(CODE_DIRECTORY))

import economy
from products import FOOD, LEGACY_PRODUCTS


class EconomyRedisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.red = redis.StrictRedis(
            host=os.environ.get("REDIS_HOST", "redis"),
            port=6379, db=15, socket_timeout=3,
        )
        cls.red.ping()

    def setUp(self):
        self.red.flushdb()
        self.farmer = "a" * 32
        self.citizen = "b" * 32

    def tearDown(self):
        self.red.flushdb()

    def ready(self, challenge):
        key = "game:challenge:" + challenge["id"]
        data = json.loads(self.red.get(key))
        data["ready_at"] = 0
        self.red.setex(key, 180, json.dumps(data))

    def farm(self, level=1):
        challenge = economy.start_challenge(self.red, self.farmer, "farmer", level)
        self.ready(challenge)
        result = economy.complete_challenge(
            self.red, self.farmer, challenge["id"], challenge["pattern"])
        return challenge, result

    def test_character_registration_keeps_role_name_and_accumulators(self):
        economy.register_player_character(self.red, self.farmer, "Rafael", "farmer")
        economy.register_player_character(self.red, self.citizen, "Nick", "citizen")
        board = economy.list_character_summaries(self.red)
        self.assertEqual(len(board), 2)
        self.assertEqual(
            [(row["name"], row["role"]) for row in board],
            [("Nick", "citizen"), ("Rafael", "farmer")],
        )
        for row in board:
            for field in ("food_produced", "food_eaten", "coins_earned_work",
                          "coins_spent_soil"):
                self.assertEqual(row[field], 0)

        # Mudança de apelido não cria outro personagem nem apaga o acumulado.
        self.red.hset("game:stats:" + self.farmer, "food_produced", 8)
        economy.register_player_character(self.red, self.farmer, "Novo nome", "farmer")
        board = economy.list_character_summaries(self.red)
        self.assertEqual(len(board), 2)
        self.assertEqual(board[1]["name"], "Novo nome")
        self.assertEqual(board[1]["food_produced"], 8)
        with self.assertRaisesRegex(ValueError, "Invalid character role"):
            economy.register_player_character(self.red, "c" * 32, "Pessoa", "admin")
        self.assertEqual(len(economy.list_character_summaries(self.red)), 2)

    def test_production_counter_only_on_successful_harvest(self):
        economy.register_player_character(self.red, self.farmer, "Farmer", "farmer")
        self.assertEqual(self.farm(1)[1]["reward"]["qty"], 1)
        self.assertEqual(self.farm(2)[1]["reward"]["qty"], 3)
        self.assertEqual(self.farm(3)[1]["reward"]["qty"], 4)
        farmer = economy.list_character_summaries(self.red)[0]
        self.assertEqual(farmer["food_produced"], 8)
        self.assertEqual(farmer["food_eaten"], 0)
        self.assertEqual(farmer["coins_earned_work"], 0)
        self.assertEqual(farmer["coins_spent_soil"], 0)

        challenge = economy.start_challenge(self.red, self.farmer, "farmer", 1)
        self.ready(challenge)
        with self.assertRaisesRegex(ValueError, "Incorrect"):
            economy.complete_challenge(self.red, self.farmer, challenge["id"],
                           [None] * len(challenge["pattern"]))
        economy.cancel_farming_challenge(self.red, self.farmer, challenge["id"])
        self.assertEqual(economy.list_character_summaries(self.red)[0]["food_produced"], 8)

    def test_work_and_food_counters_are_distinct_from_sale_income(self):
        economy.register_player_character(self.red, self.farmer, "Farm", "farmer")
        economy.register_player_character(self.red, self.citizen, "Cit", "citizen")
        self.farm(2)
        work = economy.start_challenge(self.red, self.citizen, "citizen", 3)
        raw = json.loads(self.red.get("game:challenge:" + work["id"]))
        economy.complete_challenge(self.red, self.citizen, work["id"], raw["expected"])
        for _ in range(2):
            self.red.set("game:energy:" + self.citizen, 0)
            economy.purchase_food(self.red, self.citizen)
        by_role = {row["role"]: row for row in economy.list_character_summaries(self.red)}
        self.assertEqual(by_role["citizen"]["coins_earned_work"], 15)
        self.assertEqual(by_role["citizen"]["food_eaten"], 2)
        self.assertEqual(by_role["farmer"]["food_produced"], 3)
        self.assertEqual(by_role["farmer"]["coins_earned_work"], 0)
        self.assertEqual(economy.get_player_resource_status(self.red, self.farmer)["coins"], 10)

    def test_soil_spending_counter_records_only_successful_payment(self):
        economy.register_player_character(self.red, self.farmer, "Farm", "farmer")
        self.red.set("game:soil_health:" + self.farmer, 0)
        economy.recover_soil_health(self.red, self.farmer)
        self.assertEqual(economy.list_character_summaries(self.red)[0]["coins_spent_soil"], 0)
        with self.assertRaisesRegex(ValueError, "Not enough coins"):
            economy.prepare_soil_with_coins(self.red, self.farmer)
        self.assertEqual(economy.list_character_summaries(self.red)[0]["coins_spent_soil"], 0)
        self.red.set("game:coins:" + self.farmer, 5)
        economy.prepare_soil_with_coins(self.red, self.farmer)
        self.assertEqual(economy.list_character_summaries(self.red)[0]["coins_spent_soil"], 5)
        with self.assertRaisesRegex(ValueError, "Not enough coins"):
            economy.prepare_soil_with_coins(self.red, self.farmer)
        self.assertEqual(economy.list_character_summaries(self.red)[0]["coins_spent_soil"], 5)

    def test_concurrent_transactions_do_not_duplicate_statistics(self):
        economy.register_player_character(self.red, self.farmer, "Farm", "farmer")
        economy.register_player_character(self.red, self.citizen, "Cit", "citizen")
        challenge = economy.start_challenge(self.red, self.farmer, "farmer", 1)
        self.ready(challenge)

        def harvest(_):
            try:
                economy.complete_challenge(self.red, self.farmer, challenge["id"],
                               challenge["pattern"])
                return True
            except ValueError:
                return False

        with ThreadPoolExecutor(max_workers=4) as executor:
            results = list(executor.map(harvest, range(8)))
        self.assertEqual(results.count(True), 1)
        self.red.set("game:coins:" + self.citizen, 10)
        owners = (self.citizen, "c" * 32)
        self.red.set("game:coins:" + owners[1], 10)

        def purchase(owner):
            try:
                economy.purchase_food(self.red, owner)
                return True
            except ValueError:
                return False

        with ThreadPoolExecutor(max_workers=2) as executor:
            buyers = list(executor.map(purchase, owners))
        self.assertEqual(buyers.count(True), 1)
        self.assertEqual(economy.list_character_summaries(self.red)[1]["food_produced"], 1)
        self.assertEqual(sum(int(self.red.hget("game:stats:" + owner,
                                           "food_eaten") or 0) for owner in owners), 1)
        self.assertEqual(economy.get_food_market_status(self.red)["food"], 0)

    def test_any_level_produces_only_food_and_uses_soil(self):
        for level, amount, soil in ((1, 1, 90), (2, 3, 55), (3, 4, 35)):
            with self.subTest(level=level):
                challenge, result = self.farm(level)
                self.assertNotIn("product", challenge)
                self.assertEqual(result["reward"]["qty"], amount)
                self.assertEqual(economy.get_food_market_status(self.red), {
                    FOOD: {1: 1, 2: 4, 3: 8}[level],
                })
                self.assertEqual(economy.get_player_resource_status(self.red, self.farmer)["soil_health"], soil)
                self.assertEqual(
                    set(self.red.keys("game:stock:*")), {b"game:stock:food"})

    def test_unsold_food_does_not_block_new_harvest(self):
        for _ in range(10):
            self.farm(1)
        self.assertEqual(economy.get_food_market_status(self.red), {FOOD: 10})
        self.assertEqual(self.red.lrange("game:stock:food", 0, -1),
                         [self.farmer.encode()] * 10)
        with self.assertRaisesRegex(ValueError, "Soil health too low"):
            economy.start_challenge(self.red, self.farmer, "farmer", 1)
        economy.recover_soil_health(self.red, self.farmer)
        self.farm(1)
        self.assertEqual(economy.get_food_market_status(self.red), {FOOD: 11})

    def test_citizen_earns_coins_and_buys_food(self):
        self.farm(1)
        work = economy.start_challenge(self.red, self.citizen, "citizen", 2)
        answer = json.loads(self.red.get("game:challenge:" + work["id"]))["expected"]
        economy.complete_challenge(self.red, self.citizen, work["id"], answer)
        self.assertEqual(economy.get_player_resource_status(self.red, self.citizen)["coins"], 10)
        result = economy.purchase_food(self.red, self.citizen)
        self.assertEqual(result, {"product": "food", "price": 5, "seller": self.farmer})
        self.assertEqual(economy.get_player_resource_status(self.red, self.citizen)["coins"], 5)
        self.assertEqual(economy.get_player_resource_status(self.red, self.citizen)["energy"], 80)
        self.assertEqual(economy.get_player_resource_status(self.red, self.farmer)["coins"], 5)
        self.assertEqual(economy.get_food_market_status(self.red), {"food": 0})

    def test_previous_stock_counts_as_food_and_is_sellable(self):
        self.red.rpush("game:stock:corn", self.farmer)
        self.red.rpush("game:stock:lettuce", self.farmer)
        self.assertEqual(economy.get_food_market_status(self.red), {"food": 2})
        self.red.set("game:coins:" + self.citizen, 10)
        economy.purchase_food(self.red, self.citizen)
        self.assertEqual(economy.get_food_market_status(self.red), {"food": 1})
        self.red.set("game:energy:" + self.citizen, 0)
        economy.purchase_food(self.red, self.citizen)
        self.assertEqual(economy.get_food_market_status(self.red), {"food": 0})
        self.assertEqual(economy.get_player_resource_status(self.red, self.farmer)["coins"], 10)

    def test_new_food_is_sold_before_legacy_stock(self):
        self.red.rpush("game:stock:tomato", "c" * 32)
        self.farm(1)
        self.assertEqual(economy.get_food_market_status(self.red), {"food": 2})
        self.red.set("game:coins:" + self.citizen, 5)
        result = economy.purchase_food(self.red, self.citizen)
        self.assertEqual(result["seller"], self.farmer)
        self.assertEqual(self.red.llen("game:stock:tomato"), 1)
        self.assertEqual(economy.get_food_market_status(self.red), {"food": 1})

    def test_legacy_plots_preserve_original_seller(self):
        for product, mapping in (
            ("wheat", {"product": "wheat", "qty": 1}),
            ("corn", {"crop:corn": 1}),
            ("tomato", {"stock:tomato": 1, "remaining": 1}),
        ):
            self.red.hset("game:plot:" + self.farmer + ":0", mapping=mapping)
            self.red.rpush("game:stock:" + product, self.farmer + ":0")
            self.red.set("game:coins:" + self.citizen, 10)
            self.red.set("game:energy:" + self.citizen, 0)
            result = economy.purchase_food(self.red, self.citizen)
            self.assertEqual(result["seller"], self.farmer)
            self.assertEqual(economy.get_food_market_status(self.red), {"food": 0})
            self.assertFalse(self.red.exists("game:plot:" + self.farmer + ":0"))
        self.assertEqual(economy.get_player_resource_status(self.red, self.farmer)["coins"], 15)

    def test_cancel_does_not_grant_food_or_use_soil(self):
        challenge = economy.start_challenge(self.red, self.farmer, "farmer", 1)
        self.assertEqual(economy.cancel_farming_challenge(
            self.red, self.farmer, challenge["id"]), {"id": challenge["id"]})
        self.assertEqual(economy.get_food_market_status(self.red), {"food": 0})
        self.assertEqual(economy.get_player_resource_status(self.red, self.farmer)["soil_health"], 100)
        fresh = economy.start_challenge(self.red, self.farmer, "farmer", 1)
        self.assertNotEqual(challenge["id"], fresh["id"])
        with self.assertRaisesRegex(ValueError, "expired"):
            economy.complete_challenge(self.red, self.farmer, challenge["id"], challenge["pattern"])

    def test_wrong_owner_cannot_cancel_and_citizen_not_cancellable(self):
        challenge = economy.start_challenge(self.red, self.farmer, "farmer", 1)
        with self.assertRaisesRegex(ValueError, "another player"):
            economy.cancel_farming_challenge(self.red, self.citizen, challenge["id"])
        citizen = economy.start_challenge(self.red, self.citizen, "citizen", 1)
        with self.assertRaisesRegex(ValueError, "Only Farmer"):
            economy.cancel_farming_challenge(self.red, self.citizen, citizen["id"])

    def test_repeated_or_concurrent_harvest_produces_once(self):
        challenge = economy.start_challenge(self.red, self.farmer, "farmer", 3)
        self.ready(challenge)
        def complete(_):
            try:
                economy.complete_challenge(
                    self.red, self.farmer, challenge["id"], challenge["pattern"])
                return True
            except ValueError:
                return False
        with ThreadPoolExecutor(max_workers=4) as executor:
            result = list(executor.map(complete, range(8)))
        self.assertEqual(result.count(True), 1)
        self.assertEqual(economy.get_food_market_status(self.red), {"food": 4})
        self.assertEqual(economy.get_player_resource_status(self.red, self.farmer)["soil_health"], 80)

    def test_concurrent_buyers_get_one_food_only(self):
        self.farm(1)
        buyers = ("b" * 32, "c" * 32)
        for buyer in buyers:
            self.red.set("game:coins:" + buyer, 10)
        def purchase_available_food(owner):
            try:
                economy.purchase_food(self.red, owner)
                return True
            except ValueError:
                return False
        with ThreadPoolExecutor(max_workers=2) as executor:
            result = list(executor.map(purchase_available_food, buyers))
        self.assertEqual(result.count(True), 1)
        self.assertEqual(economy.get_food_market_status(self.red), {"food": 0})
        self.assertEqual(economy.get_player_resource_status(self.red, self.farmer)["coins"], 5)

    def test_cancel_and_submit_race_is_atomic(self):
        challenge = economy.start_challenge(self.red, self.farmer, "farmer", 1)
        self.ready(challenge)
        def action(mode):
            try:
                if mode == "cancel":
                    economy.cancel_farming_challenge(self.red, self.farmer, challenge["id"])
                else:
                    economy.complete_challenge(self.red, self.farmer, challenge["id"], challenge["pattern"])
                return True
            except ValueError:
                return False
        with ThreadPoolExecutor(max_workers=2) as executor:
            result = list(executor.map(action, ("cancel", "submit")))
        self.assertEqual(result.count(True), 1)
        stock = economy.get_food_market_status(self.red)["food"]
        soil = economy.get_player_resource_status(self.red, self.farmer)["soil_health"]
        self.assertIn((stock, soil), [(0, 100), (1, 90)])

    def test_basic_and_paid_soil_care(self):
        self.red.set("game:soil_health:" + self.farmer, 0)
        self.assertEqual(economy.recover_soil_health(self.red, self.farmer)["soil_health"], 10)
        with self.assertRaisesRegex(ValueError, "below 10"):
            economy.recover_soil_health(self.red, self.farmer)
        self.red.set("game:coins:" + self.farmer, 5)
        self.assertEqual(economy.prepare_soil_with_coins(self.red, self.farmer)["soil_health"], 50)
        self.assertEqual(economy.get_player_resource_status(self.red, self.farmer)["coins"], 0)

    def test_citizen_rest_and_work_with_no_food(self):
        self.red.set("game:energy:" + self.citizen, 0)
        self.assertEqual(economy.recover_energy_with_rest(self.red, self.citizen)["energy"], 10)
        with self.assertRaisesRegex(ValueError, "below 10"):
            economy.recover_energy_with_rest(self.red, self.citizen)
        challenge = economy.start_challenge(self.red, self.citizen, "citizen", 1)
        answer = json.loads(self.red.get("game:challenge:" + challenge["id"]))["expected"]
        economy.complete_challenge(self.red, self.citizen, challenge["id"], answer)
        self.assertEqual(economy.get_player_resource_status(self.red, self.citizen)["energy"], 0)
        self.assertEqual(economy.get_player_resource_status(self.red, self.citizen)["coins"], 5)

    def test_expired_wrong_answer_and_insufficient_soil(self):
        self.red.set("game:soil_health:" + self.farmer, 9)
        with self.assertRaisesRegex(ValueError, "Soil health too low"):
            economy.start_challenge(self.red, self.farmer, "farmer", 1)
        economy.recover_soil_health(self.red, self.farmer)
        challenge = economy.start_challenge(self.red, self.farmer, "farmer", 1)
        self.ready(challenge)
        with self.assertRaisesRegex(ValueError, "Incorrect"):
            economy.complete_challenge(self.red, self.farmer, challenge["id"], [None] * 9)
        self.red.delete("game:challenge:" + challenge["id"])
        with self.assertRaisesRegex(ValueError, "expired"):
            economy.complete_challenge(self.red, self.farmer, challenge["id"], challenge["pattern"])
        self.assertEqual(economy.get_food_market_status(self.red), {"food": 0})


if __name__ == "__main__":
    unittest.main()
