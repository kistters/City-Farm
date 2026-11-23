"""One-time reset of pre-PostgreSQL game data. Run with the old server stopped."""
import os

import redis


LEGACY_PATTERNS = (
    "game:coins:*", "game:energy:*", "game:soil:*", "game:soil_health:*",
    "game:character:*", "game:characters", "game:stats:*", "game:stock:*",
    "game:challenge:*", "game:active:*", "game:history",
)


def delete_legacy_game_state(client):
    """Delete only known game namespaces, never flush a shared Redis database."""
    deleted = 0
    for pattern in LEGACY_PATTERNS:
        for key in client.scan_iter(match=pattern, count=500):
            deleted += client.unlink(key)
    return deleted


if __name__ == "__main__":
    client = redis.Redis(host=os.environ.get("REDIS_HOST", "redis"), db=0)
    print(f"Deleted {delete_legacy_game_state(client)} legacy game keys.")
