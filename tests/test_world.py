"""Unit tests for the multiplayer map, no Redis/PostgreSQL required."""
from pathlib import Path
import sys
import unittest

CODE_DIRECTORY = Path("/code")
if not CODE_DIRECTORY.is_dir():
    CODE_DIRECTORY = Path(__file__).resolve().parents[1] / "CityFarm" / "code"
sys.path.insert(0, str(CODE_DIRECTORY))

from models import PlayerProfile
from world import HEIGHT, MAP, SPAWNS, WIDTH, WorldState, is_walkable


class WorldTests(unittest.TestCase):
    def setUp(self):
        self.world = WorldState()
        self.alice = PlayerProfile.from_registration("a" * 32, "Alice")
        self.bob = PlayerProfile.from_registration("b" * 32, "Bob")

    def test_map_is_rectangular_and_spawn_points_are_walkable(self):
        self.assertEqual(len(MAP), HEIGHT)
        self.assertTrue(all(len(row) == WIDTH for row in MAP))
        self.assertTrue(all(is_walkable(*position) for position in SPAWNS.values()))

    def test_join_and_snapshot(self):
        player = self.world.join("s1", self.alice, "farmer")
        self.assertEqual(player["role"], "farmer")
        self.assertEqual((player["x"], player["y"]), SPAWNS["farmer"])
        snapshot = self.world.snapshot()
        self.assertEqual(len(snapshot["players"]), 1)
        self.assertEqual(snapshot["players"][0]["name"], "Alice")
        self.assertNotIn("last_move", snapshot["players"][0])
        self.assertEqual(snapshot["map"], list(MAP))

    def test_multiple_players_share_the_world(self):
        self.world.join("s1", self.alice, "farmer")
        self.world.join("s2", self.bob, "citizen")
        self.assertEqual(len(self.world.snapshot()["players"]), 2)
        self.assertEqual(self.world.leave("s1")["name"], "Alice")
        self.assertEqual(len(self.world.snapshot()["players"]), 1)
        self.assertIsNone(self.world.leave("s1"))

    def test_movement_is_one_cardinal_tile(self):
        self.world.join("s1", self.alice, "farmer")
        moved = self.world.move("s1", 1, 0, now=10)
        self.assertEqual((moved["x"], moved["y"]), (9, 6))
        self.assertIsNone(self.world.move("s1", 0, 1, now=10.05))
        self.assertIsNone(self.world.move("s1", 1, 0, now=10.2))  # Tree
        self.assertEqual(self.world.players["s1"]["x"], 9)

    def test_unsupported_moves_fail(self):
        self.world.join("s1", self.alice, "farmer")
        for dx, dy in ((0, 0), (1, 1), (2, 0), (True, 0), ("1", 0)):
            with self.subTest(delta=(dx, dy)):
                with self.assertRaises(ValueError):
                    self.world.move("s1", dx, dy, now=100)

    def test_unknown_player_cannot_move(self):
        with self.assertRaises(ValueError):
            self.world.move("unknown", 0, 1, now=100)

    def test_invalid_role_is_rejected(self):
        with self.assertRaises(ValueError):
            self.world.join("s1", self.alice, "admin")


if __name__ == "__main__":
    unittest.main()
