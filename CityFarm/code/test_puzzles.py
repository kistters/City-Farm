"""Testes puros: apenas Food é produzido, sem simplificar o desafio visual."""
import unittest

from products import FOOD, LEGACY_PRODUCTS
from puzzles import (
    FARM_LEVELS, MEMORY_SYMBOLS, WORK_REWARDS,
    check_solution, create_farm, create_work,
)


class PuzzleTests(unittest.TestCase):
    def test_monoculture_same_food_icon_and_exact_positions(self):
        for level, size, selected in ((1, 3, 3), (2, 4, 6)):
            for _ in range(12):
                public, board = create_farm(level)
                self.assertEqual(public["size"], size)
                self.assertEqual(len(board), size ** 2)
                symbol = public["symbol"]
                self.assertIn(symbol, MEMORY_SYMBOLS)
                self.assertEqual(board.count(symbol), selected)
                self.assertNotIn(FOOD, board)
                self.assertNotIn("product", public)
                self.assertTrue(check_solution({"public": public, "expected": board},
                                               board[:]))
                wrong = board[:]
                index = next(i for i, x in enumerate(wrong) if x is None)
                wrong[index] = symbol
                self.assertFalse(check_solution({"public": public, "expected": board},
                                                wrong))

    def test_multiculture_remains_difficult_visual_only(self):
        for _ in range(20):
            public, board = create_farm(3)
            markers = [crop for crop in board if crop is not None]
            self.assertEqual(public["size"], 4)
            self.assertEqual(len(board), 16)
            self.assertIsNone(public["symbol"])
            self.assertEqual(len(markers), 4)
            self.assertEqual(len(set(markers)), 4)
            self.assertTrue(set(markers).issubset(MEMORY_SYMBOLS))
            self.assertEqual(FARM_LEVELS[3]["production"], 4)
            wrong = board[:]
            index = next(i for i, value in enumerate(board) if value is not None)
            wrong[index] = next(x for x in MEMORY_SYMBOLS if x != wrong[index])
            self.assertFalse(check_solution({"public": public, "expected": board},
                                            wrong))
        self.assertEqual(MEMORY_SYMBOLS, LEGACY_PRODUCTS)

    def test_rules_and_invalid_answers(self):
        self.assertEqual([FARM_LEVELS[x]["soil_cost"] for x in (1, 2, 3)],
                         [10, 35, 20])
        self.assertEqual([FARM_LEVELS[x]["production"] for x in (1, 2, 3)],
                         [1, 3, 4])
        for level in (0, 4, True, "1"):
            with self.assertRaises(ValueError):
                create_farm(level)
        public, expected = create_farm(1)
        self.assertFalse(check_solution({"public": public, "expected": expected},
                                        ["fish"] * len(expected)))

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
