"""Testes puros dos puzzles, sem Redis nem Docker."""
import unittest

from puzzles import LEVEL_REWARD, check_solution, create_farm, create_work
from products import PRODUCTS


class PuzzleTests(unittest.TestCase):
    def test_farm_grids_same_crop_and_exact_positions(self):
        for level, size, selected in ((1, 3, 3), (2, 6, 6)):
            for _ in range(15):
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

    def test_extra_requires_exact_ingredient_and_position(self):
        for _ in range(12):
            public, board = create_farm(3, "carrot")
            self.assertEqual(len(board), 9)
            self.assertEqual(sum(x is not None for x in board), 4)
            self.assertTrue(set(x for x in board if x).issubset(PRODUCTS))
            wrong = board[:]
            index = next(i for i, x in enumerate(board) if x is not None)
            wrong[index] = next(x for x in PRODUCTS if x != wrong[index])
            self.assertFalse(check_solution({"public": public, "expected": board},
                                            wrong))

    def test_no_invalid_boards_or_levels(self):
        for level in (0, 4, True, "1"):
            with self.assertRaises(ValueError):
                create_farm(level, "corn")
        with self.assertRaises(ValueError):
            create_farm(1, "fish")

    def test_math_is_integer_arithmetic(self):
        for level in LEVEL_REWARD:
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
