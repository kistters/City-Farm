"""Integração com Redis DB 15 (limpo pelos testes; DB 0 nunca é tocado)."""
import json
import os
import unittest
from concurrent.futures import ThreadPoolExecutor

import redis

import economy


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

    def ready(self, public):
        key = "game:challenge:" + public["id"]
        data = json.loads(self.red.get(key))
        data["ready_at"] = 0
        self.red.setex(key, 180, json.dumps(data))

    def farm(self, level=1, product="tomato", plot=0):
        challenge = economy.start(self.red, self.farmer, "farmer", level, product, plot)
        self.ready(challenge)
        result = economy.submit(self.red, self.farmer, challenge["id"], challenge["pattern"])
        return challenge, result

    def test_monoculture_uses_soil_and_cannot_reward_twice(self):
        challenge, result = self.farm(2, "tomato", 0)
        self.assertEqual(result["reward"]["qty"], 3)
        self.assertEqual(result["reward"]["items"], [{"name": "tomato", "qty": 3}])
        self.assertEqual(economy.market(self.red)["tomato"], 3)
        self.assertEqual(economy.state(self.red, self.farmer)["soil_health"], 65)
        with self.assertRaisesRegex(ValueError, "completed"):
            economy.submit(self.red, self.farmer, challenge["id"], challenge["pattern"])
        self.assertEqual(economy.state(self.red, self.farmer)["soil_health"], 65)
        with self.assertRaisesRegex(ValueError, "occupied"):
            economy.start(self.red, self.farmer, "farmer", 1, "corn", 0)

    def test_multiculture_produces_four_actual_different_ingredients(self):
        _, result = self.farm(3, "carrot", 0)
        items = result["reward"]["items"]
        self.assertEqual(len(items), 4)
        self.assertEqual({x["qty"] for x in items}, {1})
        self.assertEqual(sum(item["qty"] for item in items), 4)
        self.assertEqual(economy.state(self.red, self.farmer)["soil_health"], 80)
        self.assertEqual(economy.state(self.red, self.farmer)["plots"][0]["qty"], 4)
        self.assertEqual(economy.state(self.red, self.farmer)["plots"][0]["product"], "mixed")
        for item in items:
            self.assertEqual(economy.market(self.red)[item["name"]], 1)

        # O lote misto permanece no terreno até a última unidade ser vendida.
        self.red.set("game:coins:" + self.citizen, 25)
        for n, item in enumerate(items):
            self.red.set("game:energy:" + self.citizen, 0)
            bought = economy.buy(self.red, self.citizen, item["name"])
            self.assertEqual(bought["seller"], self.farmer)
            plot = economy.state(self.red, self.farmer)["plots"][0]
            self.assertEqual(plot["qty"], 3 - n)
        self.assertIsNone(economy.state(self.red, self.farmer)["plots"][0]["product"])
        self.assertEqual(economy.state(self.red, self.farmer)["coins"], 20)

    def test_work_and_purchase_pay_seller_and_restore_energy(self):
        self.farm(1, "corn", 1)
        work = economy.start(self.red, self.citizen, "citizen", 2)
        raw = json.loads(self.red.get("game:challenge:" + work["id"]))
        economy.submit(self.red, self.citizen, work["id"], raw["expected"])
        self.assertEqual(economy.state(self.red, self.citizen)["coins"], 10)
        self.assertEqual(economy.state(self.red, self.citizen)["energy"], 50)
        result = economy.buy(self.red, self.citizen, "corn")
        self.assertEqual(result["seller"], self.farmer)
        self.assertEqual(economy.state(self.red, self.citizen)["coins"], 5)
        self.assertEqual(economy.state(self.red, self.citizen)["energy"], 80)
        self.assertEqual(economy.state(self.red, self.farmer)["coins"], 5)
        self.assertEqual(economy.state(self.red, self.farmer)["plots"][1]["qty"], 0)
        with self.assertRaisesRegex(ValueError, "out of stock"):
            economy.buy(self.red, self.citizen, "corn")

    def test_legacy_single_product_plot_can_still_be_sold(self):
        self.red.hset("game:plot:" + self.farmer + ":0",
                      mapping={"product": "lettuce", "qty": 1})
        self.red.rpush("game:stock:lettuce", self.farmer + ":0")
        self.red.set("game:coins:" + self.citizen, 5)
        economy.buy(self.red, self.citizen, "lettuce")
        self.assertEqual(economy.market(self.red)["lettuce"], 0)
        self.assertIsNone(economy.state(self.red, self.farmer)["plots"][0]["product"])

    def test_basic_soil_care_is_free_only_below_ten(self):
        self.red.set("game:soil_health:" + self.farmer, 0)
        self.assertEqual(economy.care_for_soil(self.red, self.farmer)["soil_health"], 10)
        with self.assertRaisesRegex(ValueError, "below 10"):
            economy.care_for_soil(self.red, self.farmer)
        self.red.set("game:soil_health:" + self.farmer, 7)
        self.assertEqual(economy.care_for_soil(self.red, self.farmer)["soil_health"], 10)
        self.assertEqual(economy.state(self.red, self.farmer)["coins"], 0)

    def test_paid_soil_care_costs_coins_and_caps_at_hundred(self):
        self.red.set("game:soil_health:" + self.farmer, 70)
        with self.assertRaisesRegex(ValueError, "Not enough coins"):
            economy.prepare_soil(self.red, self.farmer)
        self.assertEqual(economy.state(self.red, self.farmer)["soil_health"], 70)
        self.red.set("game:coins:" + self.farmer, 10)
        result = economy.prepare_soil(self.red, self.farmer)
        self.assertEqual(result, {"soil_health": 100, "cost": 5})
        self.assertEqual(economy.state(self.red, self.farmer)["coins"], 5)
        with self.assertRaisesRegex(ValueError, "already full"):
            economy.prepare_soil(self.red, self.farmer)
        self.assertEqual(economy.state(self.red, self.farmer)["coins"], 5)

    def test_concurrent_paid_care_cannot_spend_more_than_balance(self):
        self.red.set("game:soil_health:" + self.farmer, 0)
        self.red.set("game:coins:" + self.farmer, 5)

        def prepare(_):
            try:
                economy.prepare_soil(self.red, self.farmer)
                return True
            except ValueError:
                return False

        with ThreadPoolExecutor(max_workers=4) as executor:
            results = list(executor.map(prepare, range(8)))
        self.assertEqual(results.count(True), 1)
        self.assertEqual(economy.state(self.red, self.farmer)["coins"], 0)
        self.assertEqual(economy.state(self.red, self.farmer)["soil_health"], 40)

    def test_citizen_free_rest_below_ten_and_work_afterwards(self):
        self.red.set("game:energy:" + self.citizen, 0)
        self.assertEqual(economy.rest(self.red, self.citizen)["energy"], 10)
        with self.assertRaisesRegex(ValueError, "below 10"):
            economy.rest(self.red, self.citizen)
        challenge = economy.start(self.red, self.citizen, "citizen", 1)
        raw = json.loads(self.red.get("game:challenge:" + challenge["id"]))
        economy.submit(self.red, self.citizen, challenge["id"], raw["expected"])
        self.assertEqual(economy.state(self.red, self.citizen)["energy"], 0)
        self.assertEqual(economy.state(self.red, self.citizen)["coins"], 5)

    def test_soil_health_required_before_and_during_a_farm_challenge(self):
        self.red.set("game:soil_health:" + self.farmer, 9)
        with self.assertRaisesRegex(ValueError, "Soil health too low"):
            economy.start(self.red, self.farmer, "farmer", 1, "tomato", 0)
        economy.care_for_soil(self.red, self.farmer)
        challenge = economy.start(self.red, self.farmer, "farmer", 1, "tomato", 0)
        self.ready(challenge)
        self.red.set("game:soil_health:" + self.farmer, 0)
        with self.assertRaisesRegex(ValueError, "Not enough soil"):
            economy.submit(self.red, self.farmer, challenge["id"], challenge["pattern"])
        self.assertEqual(economy.market(self.red)["tomato"], 0)
        self.assertEqual(economy.care_for_soil(self.red, self.farmer)["soil_health"], 10)
        economy.submit(self.red, self.farmer, challenge["id"], challenge["pattern"])
        self.assertEqual(economy.state(self.red, self.farmer)["soil_health"], 0)

    def test_invalid_expired_wrong_owner_and_incorrect_answer(self):
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

    def test_concurrent_farm_submissions_reward_once(self):
        farm = economy.start(self.red, self.farmer, "farmer", 3, "lettuce", 0)
        self.ready(farm)

        def submit(_):
            try:
                economy.submit(self.red, self.farmer, farm["id"], farm["pattern"])
                return True
            except ValueError:
                return False

        with ThreadPoolExecutor(max_workers=4) as executor:
            results = list(executor.map(submit, range(8)))
        self.assertEqual(results.count(True), 1)
        self.assertEqual(sum(economy.market(self.red).values()), 4)
        self.assertEqual(economy.state(self.red, self.farmer)["soil_health"], 80)

    def test_concurrent_buyers_get_one_unit_only(self):
        self.farm(1, "carrot", 0)
        customers = ("b" * 32, "c" * 32)
        for customer in customers:
            self.red.set("game:coins:" + customer, 10)

        def purchase(owner):
            try:
                economy.buy(self.red, owner, "carrot")
                return True
            except ValueError:
                return False

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(purchase, customers))
        self.assertEqual(results.count(True), 1)
        self.assertEqual(economy.market(self.red)["carrot"], 0)
        self.assertEqual(economy.state(self.red, self.farmer)["coins"], 5)
        self.assertEqual(sum(economy.state(self.red, x)["coins"] for x in customers), 15)

    def test_observe_then_answer_and_cannot_use_twice(self):
        challenge = economy.start(self.red, self.farmer, "farmer", 1, "tomato", 0)
        self.assertEqual(
            economy.start(self.red, self.farmer, "farmer", 1, "tomato", 0),
            challenge,
        )
        with self.assertRaisesRegex(ValueError, "Wait"):
            economy.submit(self.red, self.farmer, challenge["id"], challenge["pattern"])
        self.ready(challenge)
        economy.submit(self.red, self.farmer, challenge["id"], challenge["pattern"])
        with self.assertRaises(ValueError):
            economy.submit(self.red, self.farmer, challenge["id"], challenge["pattern"])


if __name__ == "__main__":
    unittest.main()
