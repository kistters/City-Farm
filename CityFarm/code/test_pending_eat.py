import unittest
from unittest.mock import MagicMock, patch

from eat_orders import (
    ENQUEUE, MIGRATE, SETTLE, MAX_PENDING_PER_PRODUCT,
    enqueue_eat, migrate_legacy_order, recover_pending_orders,
)
from websocket import citizen


class PendingEatTests(unittest.TestCase):
    def test_request_is_recorded_without_scheduling_celery(self):
        with patch("websocket.enqueue_eat", return_value={"created": True, "fulfilled": 0}) as enqueue:
            with patch("websocket.dashboard_update"), patch("websocket.secrets.token_hex", return_value="abc"):
                result = citizen("tomato")
        enqueue.assert_called_once_with(unittest.mock.ANY, "tomato", "abc")
        self.assertEqual(result["fulfilled"], 0)

    def test_unknown_product_rejected(self):
        with self.assertRaises(ValueError):
            citizen("unknown")

    def test_order_persisted_in_fifo_with_deduplication_key(self):
        red = MagicMock()
        red.register_script.return_value.return_value = [1, 0]
        result = enqueue_eat(red, "corn", "abc")
        self.assertEqual(result, {"created": True, "fulfilled": 0})
        red.register_script.assert_called_once_with(ENQUEUE)
        red.register_script.return_value.assert_called_once_with(
            keys=["corn", "products:corn", "eat:queue:corn",
                  "eat:waiting:corn", "eat:fulfilled:corn",
                  "eat:pending:abc", "eat:queued:abc"],
            args=["abc", "corn", MAX_PENDING_PER_PRODUCT],
        )

    def test_full_queue_does_not_register_new_orders(self):
        red = MagicMock()
        red.register_script.return_value.return_value = [-1, 0]
        with self.assertRaisesRegex(ValueError, "Too many"):
            enqueue_eat(red, "corn", "abc")

    def test_same_id_is_not_added_twice(self):
        red = MagicMock()
        red.register_script.return_value.return_value = [-2, 0]
        self.assertFalse(enqueue_eat(red, "corn", "abc")["created"])

    def test_migration_does_not_double_count_existing_order(self):
        red = MagicMock()
        red.register_script.return_value.return_value = 1
        self.assertTrue(migrate_legacy_order(red, "tomato", "old"))
        red.register_script.assert_called_once_with(MIGRATE)
        self.assertIn("SETNX", MIGRATE)
        # Old counter is already incremented by the previous release.
        self.assertNotIn("redis.call('INCR', KEYS[4])", MIGRATE)

    def test_recovery_is_idempotent_and_settles_existing_stock(self):
        red = MagicMock()
        red.scan_iter.return_value = [b"eat:pending:old", b"eat:pending:abc"]
        red.get.side_effect = [b"corn", b"unknown"]
        with patch("eat_orders.migrate_legacy_order", return_value=True) as migrate:
            with patch("eat_orders.settle_eat") as settle:
                self.assertEqual(recover_pending_orders(red), 1)
        migrate.assert_called_once_with(red, "corn", "old")
        self.assertGreater(settle.call_count, 0)

    def test_lua_settles_orders_fifo_atomically(self):
        self.assertIn("redis.call('RPUSH', KEYS[3], ARGV[1])", ENQUEUE)
        self.assertIn("redis.call('LPOP', queue)", SETTLE)
        self.assertIn("redis.call('DECR', stock)", SETTLE)
        self.assertIn("redis.call('DEL', marker)", SETTLE)
        self.assertIn("redis.call('INCR', fulfilled)", SETTLE)

    def test_old_celery_task_returns_without_retry(self):
        from tasks import eat
        with patch("tasks.migrate_legacy_order", return_value=True), patch("tasks.notify"):
            self.assertTrue(eat.run("corn", "legacy-id"))
        self.assertNotIn("self.retry", eat.run.__code__.co_names)


if __name__ == "__main__":
    unittest.main()
