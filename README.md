# City-Farm

A local multiplayer game about farming, work, and consumption. Farmers complete memory puzzles to produce Food; Citizens solve arithmetic challenges to earn coins, buy Food, and restore Energy.

Food and coins are awarded **immediately after server-side validation**—no Celery, RabbitMQ, or waiting for crops to grow.

## Run locally

Docker Compose v2 is required.

~~~bash
docker compose up --build -d
~~~

- http://localhost/ — choose your role.
- http://localhost/farmer — memory puzzles, Soil Health, and Food production.
- http://localhost/citizen — arithmetic, coins, Energy, and eating Food.
- http://localhost/dashboard — the Food market, recent activity, and character statistics.

A phone on the same Wi-Fi can reach the game using your computer's local IP address, provided ports 80 and 8888 are accessible. **Do not expose the game to the public internet:** player IDs are not authenticated.

## Economy: only Food

There is **one tradeable product: Food**. A Farmer produces Food by completing a memory puzzle. A Citizen earns coins by completing arithmetic and buys one Food for **5 coins**, restoring up to **30 Energy** (maximum 100). The Farmer who produced the Food receives the coins.

Vegetable icons are memory clues, not separate products. No ingredient selection or individual prices exist.

Older stock from previous versions (corn, wheat, carrot, lettuce, tomato) still counts toward the total Food available. New Food sells first, followed by legacy stock, while payments still go to the original Farmer. No destructive migration is needed.

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

Counters are stored in Redis under game:stats:<player-id> and updated **atomically with the corresponding stock or balance changes**. Failed or cancelled challenges and free actions do not increase these totals. Revenue from selling Food is separate from coins earned from work.

Characters are identified by their locally stored player ID, nickname, and role. The Dashboard updates live. **Counters began when tracking was introduced**, so earlier incomplete history is not backfilled. Data persists across Docker restarts as long as Redis is preserved.

## Architecture

- Nginx serves responsive Vue 2 pages.
- Tornado provides /publihser and /dashboard WebSockets.
- Redis holds challenges (180-second TTL), Food stock and ownership, coins, Energy, Soil Health, and persistent statistics.
- puzzles.py generates and checks challenges.
- economy.py defines economic rules; Redis Lua is used for atomic updates across multiple keys.
- websocket.py handles transport and broadcasts.
- player.js keeps local Farmer and Citizen identities separate, even in the same browser.

Each valid challenge awards its reward only once, even under concurrent submissions. This is a **local architecture experiment**, not a secure internet-facing product: patterns are visible to the client, and localStorage IDs can be forged.

**Development principle:** simple code and a kind heart. SOLID and Zen of Python, applied pragmatically: readable functions, explicit responsibilities, and no unnecessary abstraction.

Legacy Proof-of-Work queues and Dish orders are not included in the Food economy. **Never run FLUSHDB against the game Redis database without a backup.**

## Tests

~~~bash
docker compose exec websocket python -m unittest test_puzzles test_economy_redis test_players
python -m unittest discover -s tests -p 'test_role_pages.py'
~~~

The integration tests clear only **Redis DB 15**; the game uses DB 0. GitHub Actions runs the Python, JavaScript, and page tests.

### Manual gameplay check

1. Open Farmer and Citizen with different player identities.
2. Complete Family Monoculture to add 1 Food to the market.
3. Harvest again without selling. Food accumulates while Soil Health allows it.
4. Complete arithmetic, earn coins, buy Food, and verify the Farmer is paid.
5. Complete Polyculture: four distinct vegetable symbols generate 4 Food.
6. Test Show Pattern Again, Cancel Challenge, soil care, and Rest.
7. Open /dashboard to view Food stock and per-character counters.
8. Verify legacy vegetable stock still sells as Food and pays the original Farmer.
9. Retry the same challenge or concurrently buy the final Food unit: no duplicate rewards or charges.

Logs: docker compose logs -f websocket.
