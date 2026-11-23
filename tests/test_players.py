from pathlib import Path
import sys
import unittest

CODE_DIRECTORY = Path("/code")
if not CODE_DIRECTORY.is_dir():
    CODE_DIRECTORY = Path(__file__).resolve().parents[1] / "CityFarm" / "code"
sys.path.insert(0, str(CODE_DIRECTORY))

from models import PlayerProfile

class PlayerTests(unittest.TestCase):
    def test_valid_profile(self):
        player = PlayerProfile.from_registration("a" * 32, "  Maria  ")
        self.assertEqual(player.player_id, "a" * 32)
        self.assertEqual(player.nickname, "Maria")
        self.assertEqual(player.as_payload(), {"id": "a" * 32, "name": "Maria"})

    def test_rejects_invalid_ids(self):
        with self.assertRaises(ValueError):
            PlayerProfile.from_registration("spoof", "Maria")

    def test_rejects_long_or_empty_nicknames(self):
        for nickname in ["", "   ", "x" * 25, "<script>"]:
            with self.subTest(nickname=nickname):
                with self.assertRaises(ValueError):
                    PlayerProfile.from_registration("a" * 32, nickname)
