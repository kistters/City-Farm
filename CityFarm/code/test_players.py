import unittest
from players import normalize_player

class PlayerTests(unittest.TestCase):
    def test_valid_profile(self):
        player = normalize_player("a" * 32, "  Maria  ")
        self.assertEqual(player, {"id": "a" * 32, "name": "Maria"})

    def test_rejects_invalid_ids(self):
        with self.assertRaises(ValueError):
            normalize_player("spoof", "Maria")

    def test_rejects_long_or_empty_nicknames(self):
        for nickname in ["", "   ", "x" * 25, "<script>"]:
            with self.subTest(nickname=nickname):
                with self.assertRaises(ValueError):
                    normalize_player("a" * 32, nickname)
