"""Integração Redis DB 15: este módulo limpa SOMENTE o banco de testes."""
import json
import os
import unittest
from concurrent.futures import ThreadPoolExecutor

import redis

import economy
from puzzles import create_farm


class EconomyRedisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.red = redis.StrictRedis(host=os.environ.get("REDIS_HOST", "redis"),
                                    port=6379, db=15, socket_timeout=3)
        cls.red.ping()

    def setUp(self):
        self.red.flushdb()
        self.farmer = "a" * 32
        self.citizen = "b" * 32

    def tearDown(self):
        self.red.flushdb()

    def ready(self, public):
        key = "game:challenge:" + public["id"]
        data = json.loads(self.red.get(key))
        data["ready_at"] = 0
        self.red.setex(key, 180, json.dumps(data))

    def test_farm_is_immediate_and_cannot_reward_twice(self):
        public = economy.start(self.red, self.farmer, "farmer", 2, "tomato", 0)
        self.ready(public)
        outcome = economy.submit(self.red, self.farmer, public["id"], public["pattern"])
        self.assertEqual(outcome["reward"], {"product": "tomato", "qty": 3, "products": {"tomato": 3}, "soil_cost": 35})
        self.assertEqual(economy.market(self.red)["tomato"], 3)
        with self.assertRaises(ValueError):
            economy.submit(self.red, self.farmer, public["id"], public["pattern"])
        self.assertEqual(economy.market(self.red)["tomato"], 3)
        with self.assertRaisesRegex(ValueError, "occupied"):
            economy.start(self.red, self.farmer, "farmer", 1, "corn", 0)

    def test_work_and_purchase_transfer_coins_to_real_seller(self):
        farm = economy.start(self.red, self.farmer, "farmer", 1, "corn", 1)
        self.ready(farm)
        economy.submit(self.red, self.farmer, farm["id"], farm["pattern"])
        work = economy.start(self.red, self.citizen, "citizen", 2)
        raw = json.loads(self.red.get("game:challenge:" + work["id"]))
        economy.submit(self.red, self.citizen, work["id"], raw["expected"])
        self.assertEqual(economy.state(self.red, self.citizen)["coins"], 10)
        bought = economy.buy(self.red, self.citizen, "corn")
        self.assertEqual(bought["seller"], self.farmer)
        self.assertEqual(economy.state(self.red, self.citizen)["coins"], 5)
        self.assertEqual(economy.state(self.red, self.citizen)["energy"], 80)
        self.assertEqual(economy.state(self.red, self.farmer)["coins"], 5)
        self.assertEqual(economy.state(self.red, self.farmer)["plots"][1]["qty"], 0)
        self.assertEqual(economy.market(self.red)["corn"], 0)
        with self.assertRaisesRegex(ValueError, "out of stock"):
            economy.buy(self.red, self.citizen, "corn")

    def test_invalid_answers_expired_challenges_and_owner(self):
        farm = economy.start(self.red, self.farmer, "farmer", 1, "wheat", 0)
        self.ready(farm)
        with self.assertRaisesRegex(ValueError, "Incorrect"):
            economy.submit(self.red, self.farmer, farm["id"], [None] * 9)
        with self.assertRaisesRegex(ValueError, "another player"):
            economy.submit(self.red, self.citizen, farm["id"], farm["pattern"])
        self.red.delete("game:challenge:" + farm["id"])
        with self.assertRaisesRegex(ValueError, "expired"):
            economy.submit(self.red, self.farmer, farm["id"], farm["pattern"])
        self.assertEqual(economy.market(self.red)["wheat"], 0)


    def test_buy_is_atomic_under_concurrent_customers(self):
        farm = economy.start(self.red, self.farmer, "farmer", 1, "carrot", 0)
        self.ready(farm)
        economy.submit(self.red, self.farmer, farm["id"], farm["pattern"])
        others = ["b" * 32, "c" * 32]
        for buyer in others:
            self.red.set("game:coins:" + buyer, 10)
        def purchase(owner):
            try:
                economy.buy(self.red, owner, "carrot")
                return True
            except ValueError:
                return False
        with ThreadPoolExecutor(max_workers=2) as executor:
            result = list(executor.map(purchase, others))
        self.assertEqual(result.count(True), 1)
        self.assertEqual(economy.market(self.red)["carrot"], 0)
        self.assertEqual(economy.state(self.red, self.farmer)["coins"], 5)
        self.assertEqual(sum(economy.state(self.red, x)["coins"] for x in others), 15)

    def test_basic_recovery_has_cap_and_is_free(self):
        self.red.set("game:soil:" + self.farmer, 0)
        self.assertEqual(economy.recover_basic(self.red, self.farmer, "farmer")["value"], 10)
        with self.assertRaisesRegex(ValueError, "only below 10"):
            economy.recover_basic(self.red, self.farmer, "farmer")
        self.red.set("game:soil:" + self.farmer, 7)
        self.assertEqual(economy.recover_basic(self.red, self.farmer, "farmer")["value"], 10)
        self.red.set("game:energy:" + self.citizen, 1)
        self.assertEqual(economy.recover_basic(self.red, self.citizen, "citizen")["value"], 10)
        self.assertEqual(economy.state(self.red, self.citizen)["coins"], 0)
        self.assertEqual(economy.state(self.red, self.farmer)["coins"], 0)

    def test_paid_soil_care_charges_only_when_possible(self):
        self.red.set("game:soil:" + self.farmer, 45)
        with self.assertRaisesRegex(ValueError, "Not enough coins"):
            economy.prepare_soil(self.red, self.farmer)
        self.assertEqual(economy.state(self.red, self.farmer)["soil_health"], 45)
        self.red.set("game:coins:" + self.farmer, 10)
        self.assertEqual(economy.prepare_soil(self.red, self.farmer),
                         {"soil_health": 85, "cost": 5})
        self.assertEqual(economy.prepare_soil(self.red, self.farmer),
                         {"soil_health": 100, "cost": 5})
        with self.assertRaisesRegex(ValueError, "already full"):
            economy.prepare_soil(self.red, self.farmer)
        self.assertEqual(economy.state(self.red, self.farmer)["coins"], 0)

    def test_soil_is_consumed_once_and_insufficient_soil_blocks_farm(self):
        self.red.set("game:soil:" + self.farmer, 10)
        with self.assertRaisesRegex(ValueError, "Not enough soil"):
            economy.start(self.red, self.farmer, "farmer", 2, "corn", 0)
        farm = economy.start(self.red, self.farmer, "farmer", 1, "corn", 0)
        self.ready(farm)
        economy.submit(self.red, self.farmer, farm["id"], farm["pattern"])
        self.assertEqual(economy.state(self.red, self.farmer)["soil_health"], 0)
        with self.assertRaisesRegex(ValueError, "expired or already"):
            economy.submit(self.red, self.farmer, farm["id"], farm["pattern"])
        self.assertEqual(economy.state(self.red, self.farmer)["soil_health"], 0)
        self.assertEqual(economy.market(self.red)["corn"], 1)

    def test_multiculture_harvest_contains_pattern_ingredients(self):
        farm = economy.start(self.red, self.farmer, "farmer", 3, "tomato", 0)
        self.ready(farm)
        expected = {name: farm["pattern"].count(name)
                    for name in economy.PRODUCTS if name in farm["pattern"]}
        outcome = economy.submit(self.red, self.farmer, farm["id"], farm["pattern"])
        self.assertEqual(outcome["reward"]["products"], expected)
        self.assertEqual(sum(economy.market(self.red).values()), 4)
        self.assertEqual(economy.state(self.red, self.farmer)["soil_health"], 80)
        self.assertEqual(economy.state(self.red, self.farmer)["plots"][0]["products"], expected)
        self.red.set("game:coins:" + self.citizen, 25)
        for product, count in expected.items():
            for _ in range(count):
                self.red.set("game:energy:" + self.citizen, 0)
                economy.buy(self.red, self.citizen, product)
        self.assertEqual(economy.state(self.red, self.farmer)["plots"][0]["qty"], 0)
        self.assertEqual(economy.state(self.red, self.farmer)["coins"], 20)

    def test_concurrent_paid_care_debits_balance_once_if_only_one_payment(self):
        self.red.set("game:soil:" + self.farmer, 0)
        self.red.set("game:coins:" + self.farmer, 5)
        def action(_):
            try:
                economy.prepare_soil(self.red, self.farmer)
                return True
            except ValueError:
                return False
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(action, range(2)))
        self.assertEqual(results.count(True), 1)
        self.assertEqual(economy.state(self.red, self.farmer)["soil_health"], 40)
        self.assertEqual(economy.state(self.red, self.farmer)["coins"], 0)

    def test_observation_period_and_same_challenge_reuse(self):
        first = economy.start(self.red, self.farmer, "farmer", 1, "tomato", 0)
        self.assertEqual(economy.start(self.red, self.farmer, "farmer", 1, "tomato", 0), first)
        with self.assertRaisesRegex(ValueError, "Wait"):
            economy.submit(self.red, self.farmer, first["id"], first["pattern"])
        self.ready(first)
        economy.submit(self.red, self.farmer, first["id"], first["pattern"])

    def test_concurrent_submissions_reward_once(self):
        farm = economy.start(self.red, self.farmer, "farmer", 3, "lettuce", 0)
        self.ready(farm)
        def action(_):
            try:
                economy.submit(self.red, self.farmer, farm["id"], farm["pattern"])
                return True
            except ValueError:
                return False
        with ThreadPoolExecutor(max_workers=4) as executor:
            results = list(executor.map(action, range(8)))
        self.assertEqual(results.count(True), 1)
        self.assertEqual(sum(economy.market(self.red).values()), 4)
        self.assertEqual(economy.state(self.red, self.farmer)["soil_health"], 80)


if __name__ == "__main__":
    unittest.main()
