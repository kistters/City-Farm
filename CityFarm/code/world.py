"""Single-process, ephemeral multiplayer overworld.

The world has no economic authority: purchases and rewards still go through the
existing PostgreSQL-backed economy. Positions and presence reset on restart.
"""
import time


WIDTH = 28
HEIGHT = 18
WALKABLE = frozenset("gpf")
SPAWNS = {"farmer": (8, 6), "citizen": (22, 6)}
LANDMARKS = (
    {"name": "Farm", "role": "farmer", "x": 6, "y": 4, "href": "/farmer"},
    {"name": "City Market", "role": "citizen", "x": 21, "y": 4, "href": "/citizen"},
)


def build_map():
    """Generate a small original tile map, shared with clients as read-only data."""
    tiles = [["g" for _ in range(WIDTH)] for _ in range(HEIGHT)]

    def rectangle(left, top, right, bottom, tile):
        for y in range(top, bottom + 1):
            for x in range(left, right + 1):
                tiles[y][x] = tile

    rectangle(1, 8, 26, 9, "p")
    rectangle(13, 2, 14, 16, "p")
    rectangle(6, 5, 7, 8, "p")
    rectangle(21, 5, 22, 8, "p")
    rectangle(2, 11, 10, 15, "f")
    rectangle(4, 2, 6, 4, "b")       # Barn
    rectangle(20, 2, 22, 4, "m")    # Market
    rectangle(24, 11, 25, 12, "h")  # Town house
    rectangle(17, 12, 21, 15, "w")
    trees = (
        (0, 0), (2, 1), (8, 2), (10, 3), (0, 5), (2, 6),
        (10, 6), (11, 11), (1, 16), (11, 16), (16, 1),
        (18, 3), (25, 2), (27, 6), (25, 15), (27, 17),
        (18, 17), (0, 12), (15, 11), (26, 9),
    )
    for x, y in trees:
        if tiles[y][x] == "g":
            tiles[y][x] = "t"
    return tuple("".join(row) for row in tiles)


MAP = build_map()


def is_walkable(x, y):
    return 0 <= x < WIDTH and 0 <= y < HEIGHT and MAP[y][x] in WALKABLE


class WorldState:
    """The Tornado process owns the authoritative positions for connected tabs."""

    def __init__(self):
        self.players = {}

    @staticmethod
    def public(player):
        return {key: player[key] for key in ("session", "id", "name", "role", "x", "y")}

    def snapshot(self):
        return {
            "map": list(MAP),
            "landmarks": list(LANDMARKS),
            "players": [self.public(p) for p in self.players.values()],
        }

    def join(self, session, profile, role):
        if role not in SPAWNS:
            raise ValueError("Choose Farmer or Citizen")
        x, y = SPAWNS[role]
        self.players[session] = {
            "session": session, "id": profile.player_id,
            "name": profile.nickname, "role": role,
            "x": x, "y": y, "last_move": 0.0,
        }
        return self.public(self.players[session])

    def leave(self, session):
        player = self.players.pop(session, None)
        return self.public(player) if player else None

    def move(self, session, dx, dy, now=None):
        if type(dx) is not int or type(dy) is not int or abs(dx) + abs(dy) != 1:
            raise ValueError("Move by exactly one tile")
        player = self.players.get(session)
        if player is None:
            raise ValueError("Join the world first")
        current = time.monotonic() if now is None else now
        if current - player["last_move"] < 0.10:
            return None
        x, y = player["x"] + dx, player["y"] + dy
        if not is_walkable(x, y):
            return None
        player.update(x=x, y=y, last_move=current)
        return self.public(player)
