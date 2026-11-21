"""Testes puros: o puzzle não depende de Redis, Tornado ou navegador."""
import unittest

from products import PRODUCTS
from puzzles import FARM_LEVELS, WORK_REWARDS, check_solution, create_farm, create_work


class PuzzleTests(unittest.TestCase):
    def test_monoculture_requires_exact_positions_and_one_ingredient(self):
        for level, size, selected in ((1, 3, 3), (2, 6, 6)):
            for _ in range(12):
                public, board = create_farm(level, "tomato")
                self.assertEqual(public["size"], size)
                self.assertEqual(len(board), size ** 2)
                self.assertEqual(board.count("tomato"), selected)
                self.assertTrue(check_solution({"public": public, "expected": board},
                                               board[:]))
                wrong = board[:]
                index = next(i for i, x in enumerate(wrong) if x is None)
                wrong[index] = "tomato"
                self.assertFalse(check_solution({"public": public, "expected": board},
                                                wrong))

    def test_multiculture_requires_exact_position_and_ingredient(self):
        for _ in range(20):
            public, board = create_farm(3, "carrot")
            self.assertEqual(len(board), 9)
            ingredients = [crop for crop in board if crop is not None]
            self.assertEqual(len(ingredients), 4)
            self.assertEqual(len(set(ingredients)), 4)
            self.assertTrue(set(ingredients).issubset(PRODUCTS))
            self.assertEqual(FARM_LEVELS[3]["production"], 4)
            wrong = board[:]
            index = next(i for i, x in enumerate(board) if x is not None)
            wrong[index] = next(crop for crop in PRODUCTS if crop != wrong[index])
            self.assertFalse(check_solution({"public": public, "expected": board},
                                            wrong))

    def test_level_rules_and_invalid_ingredients(self):
        self.assertEqual([FARM_LEVELS[n]["soil_cost"] for n in (1, 2, 3)],
                         [10, 35, 20])
        self.assertEqual([FARM_LEVELS[n]["production"] for n in (1, 2, 3)],
                         [1, 3, 4])
        for level in (0, 4, True, "1"):
            with self.subTest(level=level), self.assertRaises(ValueError):
                create_farm(level, "corn")
        with self.assertRaises(ValueError):
            create_farm(1, "fish")

    def test_math_arithmetic_and_integer_answers(self):
        for level in WORK_REWARDS:
            for _ in range(40):
                public, answer = create_work(level)
                self.assertIs(type(answer), int)
                self.assertTrue(check_solution({"public": public, "expected": answer},
                                               answer))
                self.assertFalse(check_solution({"public": public, "expected": answer},
                                                answer + 1))
                self.assertFalse(check_solution({"public": public, "expected": answer},
                                                True))
                if level == 1:
                    self.assertTrue(" + " in public["expression"] or
                                    " − " in public["expression"])
                if level == 2:
                    self.assertTrue(" × " in public["expression"] or
                                    " ÷ " in public["expression"])
                if level == 3:
                    self.assertTrue(" × " in public["expression"] or
                                    " ÷ " in public["expression"])


if __name__ == "__main__":
    unittest.main()
