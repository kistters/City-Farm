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
        self.assertEqual(outcome["reward"], {"product": "tomato", "qty": 2})
        self.assertEqual(economy.market(self.red)["tomato"], 2)
        with self.assertRaises(ValueError):
            economy.submit(self.red, self.farmer, public["id"], public["pattern"])
        self.assertEqual(economy.market(self.red)["tomato"], 2)
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

    def test_upgrade_requires_coins_and_respects_limit(self):
        with self.assertRaisesRegex(ValueError, "Not enough coins"):
            economy.upgrade_plot(self.red, self.farmer)
        self.red.set("game:coins:" + self.farmer, 100)
        for limit in (4, 5, 6):
            self.assertEqual(economy.upgrade_plot(self.red, self.farmer)["plots"], limit)
        self.assertEqual(economy.state(self.red, self.farmer)["coins"], 40)
        self.assertEqual(len(economy.state(self.red, self.farmer)["plots"]), 6)
        with self.assertRaisesRegex(ValueError, "Maximum"):
            economy.upgrade_plot(self.red, self.farmer)
        self.assertEqual(economy.state(self.red, self.farmer)["coins"], 40)

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
        self.assertEqual(economy.market(self.red)["lettuce"], 3)


if __name__ == "__main__":
    unittest.main()
