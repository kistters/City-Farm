import unittest
from unittest.mock import MagicMock

from dishes import DISHES, public_dishes
from products import PRODUCT_DIFFICULTIES, PRODUCTS
from dish_orders import ENQUEUE, FULFILL, enqueue_dish, fulfill_pending_dishes


class DishTests(unittest.TestCase):
    def test_every_ingredient_is_producible(self):
        self.assertEqual(len(PRODUCTS), 18)
        for name, recipe in DISHES.items():
            with self.subTest(name=name):
                self.assertTrue(recipe["ingredients"])
                for ingredient, count in recipe["ingredients"].items():
                    self.assertIn(ingredient, PRODUCT_DIFFICULTIES)
                    self.assertGreater(count, 0)

    def test_public_recipes_have_renderable_ingredient_text(self):
        recipes = public_dishes()
        self.assertEqual(len(recipes), len(DISHES))
        for dish in recipes:
            with self.subTest(dish=dish["id"]):
                self.assertTrue(dish["ingredients_text"])
                for ingredient, quantity in dish["ingredients"].items():
                    self.assertIn(
                        "{}× {}".format(quantity, ingredient.replace("_", " ")),
                        dish["ingredients_text"],
                    )

    def test_enqueue_increments_demand_for_each_ingredient(self):
        red = MagicMock()
        red.register_script.return_value.return_value = 1
        self.assertTrue(enqueue_dish(red, "abc", "omelette"))
        keys = red.register_script.return_value.call_args.kwargs["keys"]
        args = red.register_script.return_value.call_args.kwargs["args"]
        self.assertEqual(
            keys,
            ["dish:pending:abc", "dish:pending:ids", "dish:waiting:omelette",
             "eat:waiting:eggs", "eat:waiting:tomato"],
        )
        self.assertEqual(args, ["omelette", "abc", 2, 1])

    def test_fulfillment_checks_complete_ingredient_set(self):
        red = MagicMock()
        red.lrange.return_value = [b"abc"]
        red.get.return_value = b"omelette"
        red.register_script.return_value.return_value = 1
        self.assertEqual(fulfill_pending_dishes(red), 1)
        self.assertEqual(red.register_script.call_args.args[0], FULFILL)
        keys = red.register_script.return_value.call_args.kwargs["keys"]
        args = red.register_script.return_value.call_args.kwargs["args"]
        self.assertEqual(
            keys,
            ["dish:pending:abc", "dish:pending:ids", "dish:waiting:omelette",
             "eggs", "products:eggs", "eat:waiting:eggs",
             "tomato", "products:tomato", "eat:waiting:tomato"],
        )
        self.assertEqual(args, ["omelette", "abc", 2, 1])

    def test_no_fulfillment_if_any_ingredient_unavailable(self):
        red = MagicMock()
        red.lrange.return_value = [b"abc"]
        red.get.return_value = b"omelette"
        red.register_script.return_value.return_value = 0
        self.assertEqual(fulfill_pending_dishes(red), 0)

    def test_missing_or_already_fulfilled_order_is_ignored(self):
        red = MagicMock()
        red.lrange.return_value = [b"abc"]
        red.get.return_value = None
        self.assertEqual(fulfill_pending_dishes(red), 0)
        red.register_script.assert_not_called()

    def test_scripts_are_atomic_and_no_partial_stock_consumption(self):
        self.assertIn("if tonumber(redis.call('GET', stock) or '0') <", FULFILL)
        self.assertLess(FULFILL.index("if tonumber(redis.call('GET', stock)"), FULFILL.index("redis.call('DECRBY', stock"))
        self.assertIn("redis.call('LREM', KEYS[2], 1, ARGV[2])", FULFILL)
        self.assertIn("redis.call('RPUSH', KEYS[2], ARGV[2])", ENQUEUE)


if __name__ == "__main__":
    unittest.main()
