"""Testes econômicos com Redis DB 15; nunca apagam dados do DB 0."""
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

    def ready(self, challenge):
        key = "game:challenge:" + challenge["id"]
        data = json.loads(self.red.get(key))
        data["ready_at"] = 0
        self.red.setex(key, 180, json.dumps(data))

    def farm(self, level=1, product="tomato"):
        challenge = economy.start(self.red, self.farmer, "farmer", level, product)
        self.ready(challenge)
        reward = economy.submit(
            self.red, self.farmer, challenge["id"], challenge["pattern"])
        return challenge, reward

    def test_many_harvests_are_not_blocked_by_unsold_stock(self):
        # Produzir sem compradores não ocupa terreno nem bloqueia novo desafio.
        for _ in range(10):
            self.farm(1, "tomato")
        self.assertEqual(economy.market(self.red)["tomato"], 10)
        self.assertEqual(economy.state(self.red, self.farmer)["soil_health"], 0)
        self.assertNotIn("plots", economy.state(self.red, self.farmer))
        self.assertEqual(
            self.red.lrange("game:stock:tomato", 0, -1),
            [self.farmer.encode()] * 10,
        )
        with self.assertRaisesRegex(ValueError, "Soil health too low"):
            economy.start(self.red, self.farmer, "farmer", 1, "tomato")
        economy.care_for_soil(self.red, self.farmer)
        self.farm(1, "tomato")
        self.assertEqual(economy.market(self.red)["tomato"], 11)

    def test_monoculture_consumes_soil_and_cannot_reward_twice(self):
        challenge, result = self.farm(2, "tomato")
        self.assertEqual(result["reward"]["qty"], 3)
        self.assertEqual(
            result["reward"]["items"], [{"name": "tomato", "qty": 3}])
        self.assertEqual(economy.market(self.red)["tomato"], 3)
        self.assertEqual(economy.state(self.red, self.farmer)["soil_health"], 65)
        with self.assertRaisesRegex(ValueError, "completed"):
            economy.submit(
                self.red, self.farmer, challenge["id"], challenge["pattern"])
        self.assertEqual(economy.state(self.red, self.farmer)["soil_health"], 65)
        self.farm(1, "corn")
        self.assertEqual(economy.market(self.red)["corn"], 1)

    def test_multiculture_produces_exact_ingredients_from_pattern(self):
        challenge, result = self.farm(3, "carrot")
        items = result["reward"]["items"]
        self.assertEqual(len(items), 4)
        self.assertEqual({x["qty"] for x in items}, {1})
        self.assertEqual(
            {x["name"] for x in items},
            {crop for crop in challenge["pattern"] if crop},
        )
        self.assertEqual(sum(economy.market(self.red).values()), 4)
        self.assertEqual(economy.state(self.red, self.farmer)["soil_health"], 80)
        self.farm(3, "carrot")
        self.assertEqual(sum(economy.market(self.red).values()), 8)
        self.assertEqual(economy.state(self.red, self.farmer)["soil_health"], 60)

    def test_buy_pays_producer_and_restores_energy(self):
        self.farm(1, "corn")
        self.farm(1, "corn")
        work = economy.start(self.red, self.citizen, "citizen", 2)
        expected = json.loads(self.red.get(
            "game:challenge:" + work["id"]))["expected"]
        economy.submit(self.red, self.citizen, work["id"], expected)
        self.assertEqual(economy.state(self.red, self.citizen)["coins"], 10)
        result = economy.buy(self.red, self.citizen, "corn")
        self.assertEqual(result["seller"], self.farmer)
        self.assertEqual(economy.state(self.red, self.citizen)["coins"], 5)
        self.assertEqual(economy.state(self.red, self.citizen)["energy"], 80)
        self.assertEqual(economy.state(self.red, self.farmer)["coins"], 5)
        self.assertEqual(economy.market(self.red)["corn"], 1)
        self.red.set("game:energy:" + self.citizen, 0)
        economy.buy(self.red, self.citizen, "corn")
        self.assertEqual(economy.state(self.red, self.farmer)["coins"], 10)
        self.assertEqual(economy.market(self.red)["corn"], 0)
        with self.assertRaisesRegex(ValueError, "out of stock"):
            economy.buy(self.red, self.citizen, "corn")

    def test_legacy_single_product_stock_still_sells(self):
        old_key = "game:plot:" + self.farmer + ":0"
        self.red.hset(old_key, mapping={"product": "lettuce", "qty": 1})
        self.red.rpush("game:stock:lettuce", self.farmer + ":0")
        self.red.set("game:coins:" + self.citizen, 5)
        result = economy.buy(self.red, self.citizen, "lettuce")
        self.assertEqual(result["seller"], self.farmer)
        self.assertFalse(self.red.exists(old_key))
        self.assertEqual(economy.market(self.red)["lettuce"], 0)

    def test_legacy_mixed_lots_sell_and_do_not_block_farming(self):
        # Formato crop:<produto> (PR #23).
        old_key = "game:plot:" + self.farmer + ":0"
        self.red.hset(old_key, mapping={"crop:corn": 1, "crop:tomato": 1})
        for name in ("corn", "tomato"):
            self.red.rpush("game:stock:" + name, self.farmer + ":0")
        self.red.set("game:coins:" + self.citizen, 20)
        self.farm(1, "corn")  # Antes, o terreno ocupado impediria plantar.
        self.assertEqual(economy.market(self.red)["corn"], 2)
        economy.buy(self.red, self.citizen, "corn")
        self.assertTrue(self.red.exists(old_key))
        self.red.set("game:energy:" + self.citizen, 0)
        economy.buy(self.red, self.citizen, "tomato")
        self.assertFalse(self.red.exists(old_key))
        self.assertEqual(economy.market(self.red)["corn"], 1)
        self.red.set("game:energy:" + self.citizen, 0)
        economy.buy(self.red, self.citizen, "corn")
        self.assertEqual(economy.state(self.red, self.farmer)["coins"], 15)

    def test_previous_mixed_lot_format_survives(self):
        # Formato stock:<produto> e remaining (rascunho PR #22).
        self.red.set("game:soil:" + self.farmer, 47)
        old_key = "game:plot:" + self.farmer + ":1"
        self.red.hset(old_key, mapping={
            "stock:corn": 1, "stock:tomato": 1, "remaining": 2,
        })
        self.red.rpush("game:stock:corn", self.farmer + ":1")
        self.red.rpush("game:stock:tomato", self.farmer + ":1")
        self.red.set("game:coins:" + self.citizen, 10)
        self.assertEqual(economy.state(self.red, self.farmer)["soil_health"], 47)
        economy.buy(self.red, self.citizen, "corn")
        self.assertTrue(self.red.exists(old_key))
        self.red.set("game:energy:" + self.citizen, 0)
        economy.buy(self.red, self.citizen, "tomato")
        self.assertFalse(self.red.exists(old_key))
        self.assertEqual(economy.state(self.red, self.farmer)["coins"], 10)
        self.assertEqual(economy.state(self.red, self.farmer)["soil_health"], 47)

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
        self.assertEqual(
            economy.prepare_soil(self.red, self.farmer), {"soil_health": 100, "cost": 5})
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

    def test_soil_health_required_before_and_during_farm_challenge(self):
        self.red.set("game:soil_health:" + self.farmer, 9)
        with self.assertRaisesRegex(ValueError, "Soil health too low"):
            economy.start(self.red, self.farmer, "farmer", 1, "tomato")
        economy.care_for_soil(self.red, self.farmer)
        challenge = economy.start(self.red, self.farmer, "farmer", 1, "tomato")
        self.ready(challenge)
        self.red.set("game:soil_health:" + self.farmer, 0)
        with self.assertRaisesRegex(ValueError, "Not enough soil"):
            economy.submit(self.red, self.farmer, challenge["id"], challenge["pattern"])
        self.assertEqual(economy.market(self.red)["tomato"], 0)
        self.assertEqual(economy.care_for_soil(self.red, self.farmer)["soil_health"], 10)
        economy.submit(self.red, self.farmer, challenge["id"], challenge["pattern"])
        self.assertEqual(economy.state(self.red, self.farmer)["soil_health"], 0)

    def test_invalid_expired_wrong_owner_and_incorrect_answer(self):
        challenge = economy.start(self.red, self.farmer, "farmer", 1, "wheat")
        self.ready(challenge)
        with self.assertRaisesRegex(ValueError, "Incorrect"):
            economy.submit(self.red, self.farmer, challenge["id"], [None] * 9)
        with self.assertRaisesRegex(ValueError, "another player"):
            economy.submit(self.red, self.citizen, challenge["id"], challenge["pattern"])
        self.red.delete("game:challenge:" + challenge["id"])
        with self.assertRaisesRegex(ValueError, "expired"):
            economy.submit(self.red, self.farmer, challenge["id"], challenge["pattern"])
        self.assertEqual(economy.market(self.red)["wheat"], 0)

    def test_concurrent_farm_submissions_reward_once(self):
        challenge = economy.start(self.red, self.farmer, "farmer", 3, "lettuce")
        self.ready(challenge)

        def complete(_):
            try:
                economy.submit(
                    self.red, self.farmer, challenge["id"], challenge["pattern"])
                return True
            except ValueError:
                return False

        with ThreadPoolExecutor(max_workers=4) as executor:
            results = list(executor.map(complete, range(8)))
        self.assertEqual(results.count(True), 1)
        self.assertEqual(sum(economy.market(self.red).values()), 4)
        self.assertEqual(economy.state(self.red, self.farmer)["soil_health"], 80)

    def test_concurrent_buyers_get_one_unit_only(self):
        self.farm(1, "carrot")
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
        self.assertEqual(
            sum(economy.state(self.red, x)["coins"] for x in customers), 15)

    def test_observe_then_answer_and_cannot_use_twice(self):
        challenge = economy.start(self.red, self.farmer, "farmer", 1, "tomato")
        self.assertEqual(
            economy.start(self.red, self.farmer, "farmer", 1, "tomato"), challenge)
        with self.assertRaisesRegex(ValueError, "Wait"):
            economy.submit(self.red, self.farmer, challenge["id"], challenge["pattern"])
        self.ready(challenge)
        economy.submit(self.red, self.farmer, challenge["id"], challenge["pattern"])
        with self.assertRaises(ValueError):
            economy.submit(self.red, self.farmer, challenge["id"], challenge["pattern"])


if __name__ == "__main__":
    unittest.main()
