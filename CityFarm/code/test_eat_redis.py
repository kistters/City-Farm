"""Integration tests against the Redis development service (database 15 ONLY).

Run inside the worker container. This module clears Redis DB 15, not DB 0
where the game runs. Do not use DB 15 for unrelated data when running tests.
"""
import json
import unittest
from concurrent.futures import ThreadPoolExecutor

import redis

from eat_orders import enqueue_eat, settle_eat, migrate_legacy_order, recover_pending_orders, retire_legacy_dishes
from tasks import ACCEPT_PROOF_SCRIPT


class EventDrivenEatIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.red = redis.StrictRedis(host="redis", port=6379, db=15, socket_timeout=3)
        cls.red.ping()

    def setUp(self):
        self.red.flushdb()

    def tearDown(self):
        self.red.flushdb()

    def test_order_waits_then_harvest_fulfills_without_retry(self):
        result = enqueue_eat(self.red, "corn", "a")
        self.assertFalse(result["fulfilled"])
        self.assertEqual(self.red.get("eat:waiting:corn"), b"1")
        self.red.set("pow:challenge:one", "challenge")
        produce = self.red.register_script(ACCEPT_PROOF_SCRIPT)
        accepted = produce(
            keys=["pow:challenge:one", "products:corn", "corn",
                  "eat:queue:corn", "eat:waiting:corn", "eat:fulfilled:corn"],
            args=["challenge", json.dumps({"id": "item-1", "name": "corn"}), "corn"],
        )
        self.assertEqual(accepted, 1)
        self.assertEqual(self.red.get("corn"), b"0")
        self.assertEqual(self.red.get("eat:waiting:corn"), b"0")
        self.assertEqual(self.red.get("eat:fulfilled:corn"), b"1")
        self.assertFalse(self.red.exists("eat:pending:a"))

    def test_fifo_and_no_double_consumption_across_concurrent_harvests(self):
        for order_id in ("a", "b", "c"):
            enqueue_eat(self.red, "tomato", order_id)
        produce = self.red.register_script(ACCEPT_PROOF_SCRIPT)
        for i in range(2):
            self.red.set("pow:challenge:{}".format(i), "proof-{}".format(i))

        def harvest(i):
            return produce(
                keys=["pow:challenge:{}".format(i), "products:tomato", "tomato",
                      "eat:queue:tomato", "eat:waiting:tomato", "eat:fulfilled:tomato"],
                args=["proof-{}".format(i), json.dumps({"id": str(i)}), "tomato"],
            )

        with ThreadPoolExecutor(max_workers=4) as executor:
            results = list(executor.map(harvest, [0, 1, 0, 1]))
        self.assertEqual(sorted(results), [0, 0, 1, 1])
        self.assertFalse(self.red.exists("eat:pending:a"))
        self.assertFalse(self.red.exists("eat:pending:b"))
        self.assertTrue(self.red.exists("eat:pending:c"))
        self.assertEqual(self.red.lrange("eat:queue:tomato", 0, -1), [b"c"])
        self.assertEqual(self.red.get("tomato"), b"0")
        self.assertEqual(self.red.get("eat:waiting:tomato"), b"1")

    def test_startup_recovery_migrates_old_orders_once(self):
        self.red.set("eat:pending:old", "carrot")
        self.red.incr("eat:waiting:milk")
        self.assertEqual(recover_pending_orders(self.red), 1)
        self.assertEqual(recover_pending_orders(self.red), 0)
        self.assertEqual(self.red.lrange("eat:queue:milk", 0, -1), [b"old"])
        self.assertEqual(self.red.get("eat:waiting:milk"), b"1")
        self.red.incr("carrot")
        self.assertEqual(settle_eat(self.red, "carrot"), 1)
        self.assertEqual(settle_eat(self.red, "carrot"), 0)
        self.assertFalse(migrate_legacy_order(self.red, "carrot", "old"))
        self.assertEqual(self.red.get("eat:waiting:milk"), b"0")

    def test_retiring_old_dishes_restores_only_legacy_demand(self):
        self.red.set("dish:pending:old-omelette", "omelette")
        self.red.rpush("dish:pending:ids", "old-omelette")
        # One request for a tomato and another from the old dish.
        enqueue_eat(self.red, "tomato", "individual")
        self.red.incrby("eat:waiting:tomato", 1)
        self.red.incrby("eat:waiting:eggs", 2)
        self.red.incr("dish:waiting:omelette")
        self.assertEqual(retire_legacy_dishes(self.red), 1)
        self.assertEqual(retire_legacy_dishes(self.red), 0)
        self.assertEqual(self.red.get("eat:waiting:tomato"), b"1")
        self.assertEqual(self.red.get("eat:waiting:eggs"), b"0")
        self.assertEqual(self.red.get("dish:waiting:omelette"), b"0")
        self.assertEqual(self.red.lrange("eat:queue:tomato", 0, -1), [b"individual"])

    def test_new_request_with_stock_is_fulfilled_immediately(self):
        self.red.incr("lettuce")
        response = enqueue_eat(self.red, "lettuce", "immediate")
        self.assertTrue(response["fulfilled"])
        self.assertEqual(self.red.get("lettuce"), b"0")
        self.assertEqual(self.red.get("eat:fulfilled:potato"), b"1")

    def test_old_retry_cannot_reenqueue_fulfilled_id(self):
        self.red.incr("wheat")
        self.assertTrue(enqueue_eat(self.red, "wheat", "legacy-123")["fulfilled"])
        duplicate = enqueue_eat(self.red, "wheat", "legacy-123")
        self.assertFalse(duplicate["created"])
        self.assertEqual(self.red.get("eat:fulfilled:rice"), b"1")
        self.assertEqual(self.red.llen("eat:queue:rice"), 0)


if __name__ == "__main__":
    unittest.main()
