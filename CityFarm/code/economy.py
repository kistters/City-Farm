"""Economia do City-Farm: desafios, saldos e transações atômicas no Redis.

Funções Python expressam as regras; Lua é usado apenas onde múltiplas
chaves precisam mudar de forma indivisível (produção, pagamento e compra).
O identificador casual de jogador NÃO autentica o usuário.
"""
from collections import Counter
import json
import secrets
import time

from products import PRODUCTS
from puzzles import FARM_LEVELS, WORK_REWARDS, check_solution, create_farm, create_work

CHALLENGE_TTL = 180
INITIAL_ENERGY = 60
INITIAL_SOIL_HEALTH = 100
MAX_RESOURCE = 100
BASIC_RECOVERY = 10
ENERGY_COST = 10
FOOD_ENERGY = 30
FOOD_PRICE = 5
SOIL_PREPARE_COST = 5
SOIL_PREPARE_RECOVERY = 40
BASE_PLOTS = 3

# Desafio e saldo do solo são verificados ANTES da criação dos lotes.
# Cada campo "crop:<produto>" contém as unidades ainda não vendidas.
FINISH_FARM = """
if redis.call('GET', KEYS[1]) ~= ARGV[1] then return 0 end
if redis.call('GET', KEYS[2]) ~= ARGV[2] then return 0 end
if redis.call('EXISTS', KEYS[3]) == 1 then return -1 end
if tonumber(redis.call('GET', KEYS[4]) or '0') < tonumber(ARGV[3]) then return -2 end
local crops = cjson.decode(ARGV[5])
redis.call('DEL', KEYS[1], KEYS[2])
redis.call('DECRBY', KEYS[4], ARGV[3])
for product, count in pairs(crops) do
    redis.call('HSET', KEYS[3], 'crop:' .. product, count)
    for i = 1, count do
        redis.call('RPUSH', 'game:stock:' .. product, ARGV[4])
    end
end
return 1
"""

FINISH_WORK = """
if redis.call('GET', KEYS[1]) ~= ARGV[1] then return 0 end
if redis.call('GET', KEYS[2]) ~= ARGV[2] then return 0 end
if tonumber(redis.call('GET', KEYS[3]) or '0') < tonumber(ARGV[3]) then return -2 end
redis.call('DEL', KEYS[1], KEYS[2])
redis.call('DECRBY', KEYS[3], ARGV[3])
redis.call('INCRBY', KEYS[4], ARGV[4])
return 1
"""

# Estoque antigo com campos "product" e "qty" segue vendável, sem migração.
BUY_FOOD = """
local coins = tonumber(redis.call('GET', KEYS[1]) or '0')
local energy = tonumber(redis.call('GET', KEYS[2]) or '0')
if coins < tonumber(ARGV[1]) then return {-1, ''} end
if energy >= tonumber(ARGV[2]) then return {-2, ''} end
local item = redis.call('LINDEX', KEYS[3], 0)
if not item then return {-3, ''} end
local seller, slot = string.match(item, '^([0-9a-f]+):([0-9]+)$')
if not seller or string.len(seller) ~= 32 then return {-4, ''} end
local plot = 'game:plot:' .. seller .. ':' .. slot
local field = 'crop:' .. ARGV[3]
local count = tonumber(redis.call('HGET', plot, field) or '0')
local legacy = false
if count == 0 and redis.call('HGET', plot, 'product') == ARGV[3] then
    count = tonumber(redis.call('HGET', plot, 'qty') or '0')
    legacy = true
end
if count < 1 then return {-4, ''} end
redis.call('LPOP', KEYS[3])
redis.call('DECRBY', KEYS[1], ARGV[1])
redis.call('INCRBY', 'game:coins:' .. seller, ARGV[1])
redis.call('SET', KEYS[2], math.min(tonumber(ARGV[2]), energy + tonumber(ARGV[4])))
if legacy then
    if redis.call('HINCRBY', plot, 'qty', -1) == 0 then redis.call('DEL', plot) end
else
    if redis.call('HINCRBY', plot, field, -1) == 0 then
        redis.call('HDEL', plot, field)
        if redis.call('HLEN', plot) == 0 then redis.call('DEL', plot) end
    end
end
return {1, seller}
"""

# Recuperação gratuita é até 10, nunca +10 acima desse limite.
BASIC_RESTORE = """
local current = tonumber(redis.call('GET', KEYS[1]) or '0')
if current >= tonumber(ARGV[1]) then return -1 end
redis.call('SET', KEYS[1], ARGV[1])
return tonumber(ARGV[1])
"""

PAID_SOIL_CARE = """
local coins = tonumber(redis.call('GET', KEYS[1]) or '0')
local soil = tonumber(redis.call('GET', KEYS[2]) or '0')
if soil >= tonumber(ARGV[2]) then return -1 end
if coins < tonumber(ARGV[1]) then return -2 end
local renewed = math.min(tonumber(ARGV[2]), soil + tonumber(ARGV[3]))
redis.call('DECRBY', KEYS[1], ARGV[1])
redis.call('SET', KEYS[2], renewed)
return renewed
"""


def _text(value):
    return value.decode("utf-8") if isinstance(value, bytes) else value


def _active(owner, kind):
    return "game:active:{}:{}".format(owner, kind)


def _challenge(challenge_id):
    return "game:challenge:" + challenge_id


def _plot(owner, index):
    return "game:plot:{}:{}".format(owner, index)


def initialize_player(red, owner):
    red.setnx("game:energy:" + owner, INITIAL_ENERGY)
    red.setnx("game:soil_health:" + owner, INITIAL_SOIL_HEALTH)
    # Preservar terrenos já adquiridos em versões de teste, sem vender novos.
    red.setnx("game:plot_limit:" + owner, BASE_PLOTS)


def plot_limit(red, owner):
    initialize_player(red, owner)
    return int(red.get("game:plot_limit:" + owner))


def market(red):
    return {product: red.llen("game:stock:" + product) for product in PRODUCTS}


def state(red, owner):
    initialize_player(red, owner)
    plots = []
    for index in range(plot_limit(red, owner)):
        values = red.hgetall(_plot(owner, index))
        decoded = {_text(k): _text(v) for k, v in values.items()}
        products = {
            key.removeprefix("crop:"): int(value)
            for key, value in decoded.items() if key.startswith("crop:")
        }
        if "product" in decoded:  # legado de lotes da PR #22
            products[decoded["product"]] = int(decoded["qty"])
        plots.append({
            "index": index,
            "product": next(iter(products)) if len(products) == 1 else
                       ("mixed" if products else None),
            "qty": sum(products.values()),
            "products": products,
        })
    return {
        "coins": int(red.get("game:coins:" + owner) or 0),
        "energy": int(red.get("game:energy:" + owner) or 0),
        "soil_health": int(red.get("game:soil_health:" + owner) or 0),
        "plots": plots,
    }


def start(red, owner, kind, level, product=None, plot=None):
    if kind not in ("farmer", "citizen"):
        raise ValueError("Unknown activity")
    if type(level) is not int or level not in WORK_REWARDS:
        raise ValueError("Invalid level")
    initialize_player(red, owner)
    if kind == "farmer":
        if type(plot) is not int or plot not in range(plot_limit(red, owner)):
            raise ValueError("Choose an available plot")
        if red.exists(_plot(owner, plot)):
            raise ValueError("This plot is occupied until its food is sold")
        if int(red.get("game:soil_health:" + owner)) < FARM_LEVELS[level]["soil_cost"]:
            raise ValueError("Soil health too low. Care for the soil first.")
        public, expected = create_farm(level, product)
        public["plot"] = plot
    else:
        if int(red.get("game:energy:" + owner)) < ENERGY_COST:
            raise ValueError("Not enough energy. Rest or buy food.")
        public, expected = create_work(level)

    active = _active(owner, kind)
    old_id = _text(red.get(active))
    if old_id:
        old = red.get(_challenge(old_id))
        if old:
            return json.loads(old)["public"]
        red.delete(active)

    challenge_id = secrets.token_hex(16)
    public["id"] = challenge_id
    payload = {
        "owner": owner, "public": public, "expected": expected,
        "ready_at": time.time() + public.get("observe_seconds", 0),
    }
    if not red.set(active, challenge_id, ex=CHALLENGE_TTL, nx=True):
        old_id = _text(red.get(active))
        old = red.get(_challenge(old_id)) if old_id else None
        if old:
            return json.loads(old)["public"]
        raise ValueError("Another activity is starting; try again")
    red.setex(_challenge(challenge_id), CHALLENGE_TTL, json.dumps(payload))
    return public


def submit(red, owner, challenge_id, answer):
    if not isinstance(challenge_id, str) or len(challenge_id) != 32:
        raise ValueError("Invalid challenge")
    raw = red.get(_challenge(challenge_id))
    if not raw:
        raise ValueError("Challenge expired or already completed")
    data = json.loads(raw)
    if data["owner"] != owner:
        raise ValueError("Challenge belongs to another player")
    public = data["public"]
    if time.time() < data["ready_at"]:
        raise ValueError("Wait for the pattern to disappear")
    if not check_solution(data, answer):
        raise ValueError("Incorrect answer; you can try again")
    kind = public["kind"]
    active = _active(owner, kind)
    if kind == "farmer":
        plot = public["plot"]
        cost = FARM_LEVELS[public["level"]]["soil_cost"]
        # Dificuldade visual (células) e produção são regras distintas.
        # Só na multicultura a colheita corresponde a cada ícone mostrado.
        if public["level"] == 3:
            counts = Counter(crop for crop in data["expected"] if crop)
        else:
            counts = Counter({public["product"]: FARM_LEVELS[public["level"]]["production"]})
        outcome = int(red.register_script(FINISH_FARM)(
            keys=[_challenge(challenge_id), active, _plot(owner, plot),
                  "game:soil_health:" + owner],
            args=[raw, challenge_id, cost, "{}:{}".format(owner, plot),
                  json.dumps(counts)],
        ))
        if outcome == -1:
            raise ValueError("Plot occupied; choose a free plot")
        if outcome == -2:
            raise ValueError("Not enough soil health")
        reward = {
            "items": [{"name": product, "qty": counts[product]}
                      for product in PRODUCTS if counts[product]],
            "qty": sum(counts.values()),
            "soil_cost": cost,
        }
    else:
        coins = WORK_REWARDS[public["level"]]
        outcome = int(red.register_script(FINISH_WORK)(
            keys=[_challenge(challenge_id), active,
                  "game:energy:" + owner, "game:coins:" + owner],
            args=[raw, challenge_id, ENERGY_COST, coins],
        ))
        if outcome == -2:
            raise ValueError("Not enough energy")
        reward = {"coins": coins}
    if outcome != 1:
        raise ValueError("Challenge expired or already completed")
    return {"kind": kind, "reward": reward}


def _restore_basic(red, key):
    result = int(red.register_script(BASIC_RESTORE)(
        keys=[key], args=[BASIC_RECOVERY],
    ))
    if result == -1:
        raise ValueError("Basic care is available only below 10")
    return result


def care_for_soil(red, owner):
    initialize_player(red, owner)
    return {"soil_health": _restore_basic(red, "game:soil_health:" + owner)}


def rest(red, owner):
    initialize_player(red, owner)
    return {"energy": _restore_basic(red, "game:energy:" + owner)}


def prepare_soil(red, owner):
    initialize_player(red, owner)
    result = int(red.register_script(PAID_SOIL_CARE)(
        keys=["game:coins:" + owner, "game:soil_health:" + owner],
        args=[SOIL_PREPARE_COST, MAX_RESOURCE, SOIL_PREPARE_RECOVERY],
    ))
    if result == -1:
        raise ValueError("Soil health is already full")
    if result == -2:
        raise ValueError("Not enough coins to prepare soil")
    return {"soil_health": result, "cost": SOIL_PREPARE_COST}


def buy(red, owner, product):
    if product not in PRODUCTS:
        raise ValueError("Unknown ingredient")
    initialize_player(red, owner)
    code, seller = red.register_script(BUY_FOOD)(
        keys=["game:coins:" + owner, "game:energy:" + owner,
              "game:stock:" + product],
        args=[FOOD_PRICE, MAX_RESOURCE, product, FOOD_ENERGY],
    )
    code = int(code)
    if code != 1:
        raise ValueError({
            -1: "Not enough coins",
            -2: "Energy is already full",
            -3: "Ingredient out of stock",
            -4: "Stock needs reconciliation",
        }.get(code, "Purchase failed"))
    return {"product": product, "price": FOOD_PRICE, "seller": _text(seller)}
