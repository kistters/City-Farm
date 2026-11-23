"""Game rules; PostgreSQL stores durable state and Redis stores temporary puzzles."""
import json
import secrets
import time

from economy_repository import EconomyRepository
from challenge_repository import ChallengeRepository
from models import FOOD_PRODUCT
from puzzles import (MATH_PUZZLE_REWARDS, MEMORY_PUZZLE_LEVELS,
                     check_solution, create_math_puzzle, create_memory_puzzle)


CHALLENGE_TTL = 180
INITIAL_ENERGY = 60
INITIAL_SOIL_HEALTH = 100
MAX_RESOURCE = 100
BASIC_RECOVERY = 10
ENERGY_COST = 10
FOOD_ENERGY = 30
FOOD_PRICE = 5
SOIL_PREPARE_COST = 5
SOIL_PREPARE_RECOVERY = 40


class EconomyService:
    """Casos de uso da economia, independentes do transporte WebSocket."""

    def __init__(self, repository, challenges):
        self.repository = repository
        self.challenges = challenges

    def register_player_character(self, owner, name, role):
        if role not in ("farmer", "citizen"):
            raise ValueError("Invalid character role")
        self.repository.save_player_character(owner, name, role)

    def list_character_summaries(self):
        return self.repository.load_character_summaries()

    def initialize_player_resources(self, owner):
        self.repository.initialize_player(owner, INITIAL_ENERGY, INITIAL_SOIL_HEALTH)

    def get_food_market_status(self):
        return {FOOD_PRODUCT: self.repository.count_available_food()}

    def get_player_resource_status(self, owner):
        self.initialize_player_resources(owner)
        return self.repository.load_player_resource_status(owner)

    def start_challenge(self, owner, kind, level):
        self._validate_activity(kind, level)
        self.initialize_player_resources(owner)
        current = self.get_player_resource_status(owner)
        if kind == "farmer":
            if current["soil_health"] < MEMORY_PUZZLE_LEVELS[level]["soil_cost"]:
                raise ValueError("Soil health too low. Care for the soil first.")
            public, expected = create_memory_puzzle(level)
        else:
            if current["energy"] < ENERGY_COST:
                raise ValueError("Not enough energy. Rest or buy food.")
            public, expected = create_math_puzzle(level)

        challenge_id, old = self.challenges.load_active_challenge(owner, kind)
        if challenge_id and self.repository.is_challenge_finalized(challenge_id):
            self.challenges.clear_completed_challenge(owner, kind, challenge_id)
            challenge_id, old = self.challenges.load_active_challenge(owner, kind)
            if old:
                raise ValueError("Previous activity is being cleared; try again")
        if old:
            return json.loads(old)["public"]
        if challenge_id:
            self.challenges.remove_stale_active_challenge(owner, kind)

        challenge_id = secrets.token_hex(16)
        public["id"] = challenge_id
        payload = json.dumps({
            "owner": owner, "public": public, "expected": expected,
            "ready_at": time.time() + public.get("observe_seconds", 0),
        })
        if not self.challenges.save_new_challenge(owner, kind, challenge_id, payload, CHALLENGE_TTL):
            _, old = self.challenges.load_active_challenge(owner, kind)
            if old:
                return json.loads(old)["public"]
            raise ValueError("Another activity is starting; try again")
        return public

    def complete_challenge(self, owner, challenge_id, answer):
        self._validate_challenge_id(challenge_id)
        raw = self.challenges.load_challenge(challenge_id)
        if not raw:
            raise ValueError("Challenge expired or already completed")
        data = json.loads(raw)
        if data["owner"] != owner:
            raise ValueError("Challenge belongs to another player")
        if time.time() < data["ready_at"]:
            raise ValueError("Wait for the pattern to disappear")
        if not check_solution(data, answer):
            raise ValueError("Incorrect answer; you can try again")

        public = data["public"]
        if public["kind"] == "farmer":
            cost = MEMORY_PUZZLE_LEVELS[public["level"]]["soil_cost"]
            quantity = MEMORY_PUZZLE_LEVELS[public["level"]]["production"]
            outcome = self.repository.finalize_challenge(
                self.challenges, raw, challenge_id, owner, "farmer", cost, quantity)
            if outcome == -2:
                raise ValueError("Not enough soil health")
            reward = {"qty": quantity, "soil_cost": cost}
        else:
            coins = MATH_PUZZLE_REWARDS[public["level"]]
            outcome = self.repository.finalize_challenge(
                self.challenges, raw, challenge_id, owner, "citizen", ENERGY_COST, coins)
            if outcome == -2:
                raise ValueError("Not enough energy")
            reward = {"coins": coins}
        if outcome != 1:
            raise ValueError("Challenge expired or already completed")
        return {"kind": public["kind"], "reward": reward}

    def cancel_farming_challenge(self, owner, challenge_id):
        self._validate_challenge_id(challenge_id)
        raw = self.challenges.load_challenge(challenge_id)
        if not raw:
            raise ValueError("Challenge expired or already completed")
        challenge = json.loads(raw)
        if challenge["owner"] != owner:
            raise ValueError("Challenge belongs to another player")
        kind = challenge["public"]["kind"]
        if kind != "farmer":
            raise ValueError("Only Farmer challenges can be cancelled here")
        if self.repository.finalize_challenge(
                self.challenges, raw, challenge_id, owner, kind, cancelled=True) != 1:
            raise ValueError("Challenge expired or already completed")
        return {"id": challenge_id}

    def recover_soil_health(self, owner):
        self.initialize_player_resources(owner)
        return {"soil_health": self._restore_minimum_resource(owner, "soil_health")}

    def recover_energy_with_rest(self, owner):
        self.initialize_player_resources(owner)
        return {"energy": self._restore_minimum_resource(owner, "energy")}

    def prepare_soil_with_coins(self, owner):
        self.initialize_player_resources(owner)
        result = self.repository.pay_to_prepare_soil(
            owner, SOIL_PREPARE_COST, MAX_RESOURCE, SOIL_PREPARE_RECOVERY)
        if result == -1:
            raise ValueError("Soil health is already full")
        if result == -2:
            raise ValueError("Not enough coins to prepare soil")
        return {"soil_health": result, "cost": SOIL_PREPARE_COST}

    def purchase_food(self, owner):
        self.initialize_player_resources(owner)
        code, seller = self.repository.purchase_next_food(
            owner, FOOD_PRICE, MAX_RESOURCE, FOOD_ENERGY)
        if code != 1:
            raise ValueError({
                -1: "Not enough coins", -2: "Energy is already full",
                -3: "Food out of stock", -4: "Stock needs reconciliation",
            }.get(code, "Purchase failed"))
        return {"product": FOOD_PRODUCT, "price": FOOD_PRICE, "seller": seller}

    @staticmethod
    def _validate_activity(kind, level):
        if kind not in ("farmer", "citizen"):
            raise ValueError("Unknown activity")
        available_levels = (MEMORY_PUZZLE_LEVELS if kind == "farmer"
                            else MATH_PUZZLE_REWARDS)
        if type(level) is not int or level not in available_levels:
            raise ValueError("Invalid level")

    @staticmethod
    def _validate_challenge_id(challenge_id):
        if not isinstance(challenge_id, str) or len(challenge_id) != 32:
            raise ValueError("Invalid challenge")

    def _restore_minimum_resource(self, owner, resource):
        result = self.repository.restore_to_minimum(owner, resource, BASIC_RECOVERY)
        if result == -1:
            raise ValueError("Basic care is available only below 10")
        return result


def _service(red):
    """Adaptador da API de funções legada para o novo serviço."""
    return EconomyService(EconomyRepository(), ChallengeRepository(red))


def register_player_character(red, owner, name, role):
    return _service(red).register_player_character(owner, name, role)


def list_character_summaries(red):
    return _service(red).list_character_summaries()


def initialize_player_resources(red, owner):
    return _service(red).initialize_player_resources(owner)


def get_food_market_status(red):
    return _service(red).get_food_market_status()


def get_player_resource_status(red, owner):
    return _service(red).get_player_resource_status(owner)


def start_challenge(red, owner, kind, level):
    return _service(red).start_challenge(owner, kind, level)


def complete_challenge(red, owner, challenge_id, answer):
    return _service(red).complete_challenge(owner, challenge_id, answer)


def cancel_farming_challenge(red, owner, challenge_id):
    return _service(red).cancel_farming_challenge(owner, challenge_id)


def recover_soil_health(red, owner):
    return _service(red).recover_soil_health(owner)


def recover_energy_with_rest(red, owner):
    return _service(red).recover_energy_with_rest(owner)


def prepare_soil_with_coins(red, owner):
    return _service(red).prepare_soil_with_coins(owner)


def purchase_food(red, owner):
    return _service(red).purchase_food(owner)
