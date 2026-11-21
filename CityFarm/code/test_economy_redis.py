"""Economia Food com Redis DB 15 (não toca o DB 0 do jogo)."""
import json
import os
import unittest
from concurrent.futures import ThreadPoolExecutor

import redis

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
        challenge = economy.start(self.red, self.farmer, "farmer", level)
        self.ready(challenge)
        result = economy.submit(
            self.red, self.farmer, challenge["id"], challenge["pattern"])
        return challenge, result

    def test_any_level_produces_only_food_and_uses_soil(self):
        for level, amount, soil in ((1, 1, 90), (2, 3, 55), (3, 4, 35)):
            with self.subTest(level=level):
                challenge, result = self.farm(level)
                self.assertNotIn("product", challenge)
                self.assertEqual(result["reward"]["qty"], amount)
                self.assertEqual(economy.market(self.red), {
                    FOOD: {1: 1, 2: 4, 3: 8}[level],
                })
                self.assertEqual(economy.state(self.red, self.farmer)["soil_health"], soil)
                self.assertEqual(
                    set(self.red.keys("game:stock:*")), {b"game:stock:food"})

    def test_unsold_food_does_not_block_new_harvest(self):
        for _ in range(10):
            self.farm(1)
        self.assertEqual(economy.market(self.red), {FOOD: 10})
        self.assertEqual(self.red.lrange("game:stock:food", 0, -1),
                         [self.farmer.encode()] * 10)
        with self.assertRaisesRegex(ValueError, "Soil health too low"):
            economy.start(self.red, self.farmer, "farmer", 1)
        economy.care_for_soil(self.red, self.farmer)
        self.farm(1)
        self.assertEqual(economy.market(self.red), {FOOD: 11})

    def test_citizen_earns_coins_and_buys_food(self):
        self.farm(1)
        work = economy.start(self.red, self.citizen, "citizen", 2)
        answer = json.loads(self.red.get("game:challenge:" + work["id"]))["expected"]
        economy.submit(self.red, self.citizen, work["id"], answer)
        self.assertEqual(economy.state(self.red, self.citizen)["coins"], 10)
        result = economy.buy(self.red, self.citizen)
        self.assertEqual(result, {"product": "food", "price": 5, "seller": self.farmer})
        self.assertEqual(economy.state(self.red, self.citizen)["coins"], 5)
        self.assertEqual(economy.state(self.red, self.citizen)["energy"], 80)
        self.assertEqual(economy.state(self.red, self.farmer)["coins"], 5)
        self.assertEqual(economy.market(self.red), {"food": 0})

    def test_previous_stock_counts_as_food_and_is_sellable(self):
        self.red.rpush("game:stock:corn", self.farmer)
        self.red.rpush("game:stock:lettuce", self.farmer)
        self.assertEqual(economy.market(self.red), {"food": 2})
        self.red.set("game:coins:" + self.citizen, 10)
        economy.buy(self.red, self.citizen)
        self.assertEqual(economy.market(self.red), {"food": 1})
        self.red.set("game:energy:" + self.citizen, 0)
        economy.buy(self.red, self.citizen)
        self.assertEqual(economy.market(self.red), {"food": 0})
        self.assertEqual(economy.state(self.red, self.farmer)["coins"], 10)

    def test_new_food_is_sold_before_legacy_stock(self):
        self.red.rpush("game:stock:tomato", "c" * 32)
        self.farm(1)
        self.assertEqual(economy.market(self.red), {"food": 2})
        self.red.set("game:coins:" + self.citizen, 5)
        result = economy.buy(self.red, self.citizen)
        self.assertEqual(result["seller"], self.farmer)
        self.assertEqual(self.red.llen("game:stock:tomato"), 1)
        self.assertEqual(economy.market(self.red), {"food": 1})

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
            result = economy.buy(self.red, self.citizen)
            self.assertEqual(result["seller"], self.farmer)
            self.assertEqual(economy.market(self.red), {"food": 0})
            self.assertFalse(self.red.exists("game:plot:" + self.farmer + ":0"))
        self.assertEqual(economy.state(self.red, self.farmer)["coins"], 15)

    def test_cancel_does_not_grant_food_or_use_soil(self):
        challenge = economy.start(self.red, self.farmer, "farmer", 1)
        self.assertEqual(economy.cancel_challenge(
            self.red, self.farmer, challenge["id"]), {"id": challenge["id"]})
        self.assertEqual(economy.market(self.red), {"food": 0})
        self.assertEqual(economy.state(self.red, self.farmer)["soil_health"], 100)
        fresh = economy.start(self.red, self.farmer, "farmer", 1)
        self.assertNotEqual(challenge["id"], fresh["id"])
        with self.assertRaisesRegex(ValueError, "expired"):
            economy.submit(self.red, self.farmer, challenge["id"], challenge["pattern"])

    def test_wrong_owner_cannot_cancel_and_citizen_not_cancellable(self):
        challenge = economy.start(self.red, self.farmer, "farmer", 1)
        with self.assertRaisesRegex(ValueError, "another player"):
            economy.cancel_challenge(self.red, self.citizen, challenge["id"])
        citizen = economy.start(self.red, self.citizen, "citizen", 1)
        with self.assertRaisesRegex(ValueError, "Only Farmer"):
            economy.cancel_challenge(self.red, self.citizen, citizen["id"])

    def test_repeated_or_concurrent_harvest_produces_once(self):
        challenge = economy.start(self.red, self.farmer, "farmer", 3)
        self.ready(challenge)
        def complete(_):
            try:
                economy.submit(
                    self.red, self.farmer, challenge["id"], challenge["pattern"])
                return True
            except ValueError:
                return False
        with ThreadPoolExecutor(max_workers=4) as executor:
            result = list(executor.map(complete, range(8)))
        self.assertEqual(result.count(True), 1)
        self.assertEqual(economy.market(self.red), {"food": 4})
        self.assertEqual(economy.state(self.red, self.farmer)["soil_health"], 80)

    def test_concurrent_buyers_get_one_food_only(self):
        self.farm(1)
        buyers = ("b" * 32, "c" * 32)
        for buyer in buyers:
            self.red.set("game:coins:" + buyer, 10)
        def buy(owner):
            try:
                economy.buy(self.red, owner)
                return True
            except ValueError:
                return False
        with ThreadPoolExecutor(max_workers=2) as executor:
            result = list(executor.map(buy, buyers))
        self.assertEqual(result.count(True), 1)
        self.assertEqual(economy.market(self.red), {"food": 0})
        self.assertEqual(economy.state(self.red, self.farmer)["coins"], 5)

    def test_cancel_and_submit_race_is_atomic(self):
        challenge = economy.start(self.red, self.farmer, "farmer", 1)
        self.ready(challenge)
        def action(mode):
            try:
                if mode == "cancel":
                    economy.cancel_challenge(self.red, self.farmer, challenge["id"])
                else:
                    economy.submit(self.red, self.farmer, challenge["id"], challenge["pattern"])
                return True
            except ValueError:
                return False
        with ThreadPoolExecutor(max_workers=2) as executor:
            result = list(executor.map(action, ("cancel", "submit")))
        self.assertEqual(result.count(True), 1)
        stock = economy.market(self.red)["food"]
        soil = economy.state(self.red, self.farmer)["soil_health"]
        self.assertIn((stock, soil), [(0, 100), (1, 90)])

    def test_basic_and_paid_soil_care(self):
        self.red.set("game:soil_health:" + self.farmer, 0)
        self.assertEqual(economy.care_for_soil(self.red, self.farmer)["soil_health"], 10)
        with self.assertRaisesRegex(ValueError, "below 10"):
            economy.care_for_soil(self.red, self.farmer)
        self.red.set("game:coins:" + self.farmer, 5)
        self.assertEqual(economy.prepare_soil(self.red, self.farmer)["soil_health"], 50)
        self.assertEqual(economy.state(self.red, self.farmer)["coins"], 0)

    def test_citizen_rest_and_work_with_no_food(self):
        self.red.set("game:energy:" + self.citizen, 0)
        self.assertEqual(economy.rest(self.red, self.citizen)["energy"], 10)
        with self.assertRaisesRegex(ValueError, "below 10"):
            economy.rest(self.red, self.citizen)
        challenge = economy.start(self.red, self.citizen, "citizen", 1)
        answer = json.loads(self.red.get("game:challenge:" + challenge["id"]))["expected"]
        economy.submit(self.red, self.citizen, challenge["id"], answer)
        self.assertEqual(economy.state(self.red, self.citizen)["energy"], 0)
        self.assertEqual(economy.state(self.red, self.citizen)["coins"], 5)

    def test_expired_wrong_answer_and_insufficient_soil(self):
        self.red.set("game:soil_health:" + self.farmer, 9)
        with self.assertRaisesRegex(ValueError, "Soil health too low"):
            economy.start(self.red, self.farmer, "farmer", 1)
        economy.care_for_soil(self.red, self.farmer)
        challenge = economy.start(self.red, self.farmer, "farmer", 1)
        self.ready(challenge)
        with self.assertRaisesRegex(ValueError, "Incorrect"):
            economy.submit(self.red, self.farmer, challenge["id"], [None] * 9)
        self.red.delete("game:challenge:" + challenge["id"])
        with self.assertRaisesRegex(ValueError, "expired"):
            economy.submit(self.red, self.farmer, challenge["id"], challenge["pattern"])
        self.assertEqual(economy.market(self.red), {"food": 0})


if __name__ == "__main__":
    unittest.main()
