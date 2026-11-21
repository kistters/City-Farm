import unittest
from unittest.mock import MagicMock, patch

from high_helpers import decr_resource_if_available
from websocket import citizen, dashboard_update


class PendingEatTests(unittest.TestCase):
    def test_consume_passes_unique_pending_order_to_lua(self):
        red = MagicMock()
        red.register_script.return_value.return_value = 1
        self.assertTrue(decr_resource_if_available(red, "tomato", request_id="abc"))
        red.register_script.return_value.assert_called_once_with(
            keys=["tomato", "products:tomato", "eat:pending:abc", "eat:waiting:tomato"],
            args=[0, "tomato"],
        )

    def test_legacy_consumption_does_not_settle_new_order(self):
        red = MagicMock()
        red.register_script.return_value.return_value = 1
        decr_resource_if_available(red, "corn")
        keys = red.register_script.return_value.call_args.kwargs["keys"]
        self.assertEqual(keys[2], "eat:pending:legacy")

    def test_new_eat_order_increments_pending_counter(self):
        with patch("websocket.r") as red, patch("websocket.eat") as task, patch("websocket.dashboard_update"):
            with patch("websocket.secrets.token_hex", return_value="abc"):
                citizen("tomato")
            red.set.assert_called_once_with("eat:pending:abc", "tomato")
            red.incr.assert_called_once_with("eat:waiting:tomato")
            task.apply_async.assert_called_once_with(
                ("tomato", "abc"), queue="eating", serializer="json",
            )

    def test_rejected_unknown_product_does_not_enqueue(self):
        with patch("websocket.eat") as task:
            with self.assertRaises(ValueError):
                citizen("unknown")
            task.apply_async.assert_not_called()


if __name__ == "__main__":
    unittest.main()
