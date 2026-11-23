# City-Farm

A local multiplayer game about farming, work, and consumption. Enter a shared pixel-art village, then play as a Farmer who grows Food or a Citizen who earns coins to buy it.

Food and coins are awarded **immediately after server-side validation**—no Celery, RabbitMQ, or waiting for crops to grow.

## Run locally

Docker Compose v2 is required.

~~~bash
docker compose up --build -d
~~~

- http://localhost/ — explore the shared pixel-art village, meet players, and choose a role.
- http://localhost/farmer — memory puzzles, Soil Health, and Food production.
- http://localhost/citizen — arithmetic, coins, Energy, and eating Food.
- http://localhost/dashboard — the Food market, recent activity, and character statistics.

A phone on the same Wi-Fi can reach the game using your computer's local IP address, provided ports 80 and 8888 are accessible. **Do not expose the game to the public internet:** player IDs are not authenticated.

## Multiplayer village (experimental)

The home page now shows a small top-down **28×18 tile village**, rendered with
HTML Canvas and original pixel art. Join as **Farmer** or **Citizen** and use
**WASD**, **arrow keys**, or the touch direction buttons to walk. Other players
on the same server appear immediately with nicknames. Walk next to the Farm
(Farmer) or Market (Citizen) and press **E** or click **Enter building** to
open the existing role gameplay. The Dashboard remains accessible from the
navigation.

The Tornado `/world` WebSocket owns player positions. It accepts one-tile
cardinal movements, blocks walls and water, and broadcasts join/move/leave
messages to connected browsers. Rendering interpolates movement between tiles.
The **world state is in memory only**: disconnecting removes a character,
restarting Tornado resets positions, and each connected tab has its own avatar.
The player economy, stock, and statistics remain in PostgreSQL. Redis still
holds temporary puzzles and recent activity.

This is an intentionally **single-process, local-network prototype**. It does
not implement accounts, secure login, reconnect-to-last-position, collisions
between avatars, chat, spatial interest management, or persistence of map
positions. Player IDs are untrusted; keep it off the public internet.

## Economy: only Food

There is **one tradeable product: Food**. A Farmer produces Food by completing a memory puzzle. A Citizen earns coins by completing arithmetic and buys one Food for **5 coins**, restoring up to **30 Energy** (maximum 100). The Farmer who produced the Food receives the coins.

Vegetable icons are memory clues, not separate products. No ingredient selection or individual prices exist.

Food is stored in PostgreSQL lots with `farmer_id`, `quantity`, and `created_at`. Purchases consume the oldest lot and pay its Farmer in the same database transaction.

## Farmer

| Difficulty | Memory puzzle | Food produced | Soil Health cost |
|---|---|---:|---:|
| Family Monoculture | 3×3, one vegetable | 1 | 10 |
| Large-Scale Monoculture | 4×4, six positions with one vegetable | 3 | 35 |
| Polyculture | 4×4, four different vegetables | 4 | 20 |

Vegetables use pixel-art icons. Monoculture selects one vegetable for that challenge; Polyculture uses four different vegetable symbols. **All three difficulties produce Food**, not different crops.

**Show Pattern Again** reveals the pattern without clearing the player's selections. **Cancel Challenge** ends an attempt without consuming Soil Health or producing Food.

Farmers may produce repeatedly, even with unsold stock. **Soil Health (0–100)** limits production, not plots. **Care for Soil** is free below 10 and restores Soil Health up to 10. **Prepare Soil** costs 5 coins and restores up to 40 Soil Health, capped at 100.

## Citizen

| Work level | Arithmetic | Coins earned |
|---|---|---:|
| Intern | Addition and subtraction | 5 |
| Employee | Multiplication and exact division | 10 |
| Consultant | Expressions with multiple operations | 15 |

Successful work consumes 10 Energy. A Citizen starts with 60/100 Energy and zero coins. **Rest** is free when Energy is below 10 and restores it up to 10. **Eat Food** buys one Food for 5 coins and restores up to 30 Energy.

## Pixel-art identity and layout

A shared spritesheet at CityFarm/front/css/images/pixel-cityfarm.png displays a hoe, tractor, the three farm levels, sleeping, a bowl of Food, three career levels, and vegetables. The wallet uses a separate gold pixel-art coin at CityFarm/front/css/images/pixel-coin.svg.

Farmer and Citizen use matching screens: player identity, a coin icon and numeric balance, a labeled Soil Health or Energy bar, two action cards, and the challenge area. The wallet icon has accessible alt text, even though the word "Coins" is no longer visible beside the number.

**All user-facing text and feedback are in English.**

## Dashboard: market and persistent character statistics

The Dashboard contains the total Food stock, a recent activity feed, and per-character totals:

| Counter | When it increases |
|---|---|
| Food produced | A Farmer successfully completes a memory puzzle (+1, +3, or +4) |
| Food eaten | A Citizen buys and eats one Food |
| Coins earned from work | A Citizen completes an arithmetic challenge (+5, +10, or +15) |
| Coins spent on soil | A Farmer pays 5 coins to Prepare Soil |

Counters are stored in PostgreSQL and updated **atomically with the corresponding stock or balance changes**. Failed or cancelled challenges and free actions do not increase these totals. Revenue from selling Food is separate from coins earned from work.

Characters are identified by their locally stored player ID, nickname, and role. The Dashboard updates live. **Counters began when tracking was introduced**, so earlier incomplete history is not backfilled. The dashboard shows the first 100 registered characters ordered by role and name. Player state persists in the PostgreSQL named volume across container recreation; `docker compose down -v` deletes that volume.

## Architecture

- Nginx serves responsive Vue 2 pages.
- Tornado provides /player and /dashboard WebSockets.
- PostgreSQL stores players, balances, resources, statistics, Food lots, purchase records, and challenge completion/cancellation receipts.
- Redis holds temporary challenges (180-second TTL) and a bounded feed of 50 recent events. Losing Redis interrupts active puzzles but does not erase durable player state.
- puzzles.py generates and checks challenges.
- economy.py defines economic rules; economy_repository.py owns SQL transactions and challenge_repository.py owns temporary Redis payloads.
- The server creates the initial SQL schema on startup. Rewards and durable challenge receipts commit together before Redis cleanup; retries cannot award twice.
- Purchases serialize FIFO inventory selection, lock player rows in a stable order, and commit stock, debit, credit, counters, and purchase record together.
- websocket.py handles transport and broadcasts.
- player.js keeps local Farmer and Citizen identities separate, even in the same browser.

Each valid challenge awards its reward only once, even under concurrent submissions. This is a **local architecture experiment**, not a secure internet-facing product: patterns are visible to the client, and localStorage IDs can be forged.

**Development principle:** simple code and a kind heart. SOLID and Zen of Python, applied pragmatically: readable functions, explicit responsibilities, and no unnecessary abstraction.

Legacy Proof-of-Work queues and Dish orders are not included in the Food economy. **Never run FLUSHDB against the game Redis database without a backup.**

## Tests

~~~bash
docker compose up -d postgres redis
docker compose exec postgres createdb -U cityfarm cityfarm_test # once
docker compose run --rm websocket python -m unittest discover -s /tests -p 'test_*.py'
~~~

The integration tests clear **Redis DB 15** and tables in **cityfarm_test**, never the game database. Tests require TEST_DATABASE_URL and reject any database name other than cityfarm_test. Compose supplies it; GitHub Actions provides isolated PostgreSQL and Redis services.

### Manual gameplay check

1. Open Farmer and Citizen with different player identities.
2. Complete Family Monoculture to add 1 Food to the market.
3. Harvest again without selling. Food accumulates while Soil Health allows it.
4. Complete arithmetic, earn coins, buy Food, and verify the Farmer is paid.
5. Complete Polyculture: four distinct vegetable symbols generate 4 Food.
6. Test Show Pattern Again, Cancel Challenge, soil care, and Rest.
7. Open /dashboard to view Food stock and per-character counters.
8. Restart Redis and verify balances, stock, and statistics survive (active puzzles are temporary).
9. Retry the same challenge or concurrently buy the final Food unit: no duplicate rewards or charges.

Logs: docker compose logs -f websocket.

## Switching from the Redis-only version

This change deliberately starts a new economy: old balances, stock, profiles, statistics,
active challenges, and recent events are discarded, not imported. Browser identities
can register again. Stop the old server before cleanup so it cannot recreate old keys:

~~~bash
docker compose stop websocket
docker compose up -d postgres redis
docker compose build websocket
docker compose run --rm websocket python reset_legacy_redis.py
docker compose up -d websocket
~~~

The reset uses SCAN and UNLINK only for known game namespaces; it never calls FLUSHDB
and does not touch PostgreSQL or unrelated Redis keys. Deleted old state cannot be
recovered without an existing backup. Do not run the reset again while players are active.

PostgreSQL uses a named volume, a health check, and internal-only networking. The
Compose credentials are for local development. DATABASE_URL configures the server;
use separate credentials and backups for a hosted environment. Database connections
are currently synchronous and opened per operation; connection pooling and async I/O
remain future scaling work, as do paginated dashboard navigation and audit retention.
