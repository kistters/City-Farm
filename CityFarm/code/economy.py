"""Economia e desafios em Redis: conclusão e compra atômicas em Lua.

Protótipo local sem autenticação: o identificador casual do jogador não é
uma credencial. Não exponha o jogo à Internet pública.
"""
import json
import secrets
import time

from products import PRODUCTS
from puzzles import create_farm, create_work, check_solution, LEVEL_REWARD

CHALLENGE_TTL = 180
INITIAL_ENERGY = 60
ENERGY_COST = 10
FOOD_ENERGY = 30
MAX_ENERGY = 100
FOOD_PRICE = 5
PLOTS = 3
INITIAL_SOIL_HEALTH = 100
SOIL_COST = {1: 10, 2: 35, 3: 20}
SOIL_CARE_COST = 5
SOIL_CARE_GAIN = 40
BASIC_RECOVERY = 10

FINISH_FARM = """
-- Validate both the challenge and resources before changing anything.
if redis.call('GET', KEYS[1]) ~= ARGV[1] then return 0 end
if redis.call('GET', KEYS[2]) ~= ARGV[2] then return 0 end
if redis.call('EXISTS', KEYS[3]) == 1 then return -1 end
if tonumber(redis.call('GET', KEYS[4]) or '0') < tonumber(ARGV[3]) then return -2 end
local products = cjson.decode(ARGV[4])
local total = 0
for name, quantity in pairs(products) do
    if quantity < 1 or not string.match(name, '^[a-z_]+$') then return -3 end
    total = total + quantity
end
redis.call('DEL', KEYS[1], KEYS[2])
redis.call('DECRBY', KEYS[4], ARGV[3])
redis.call('HSET', KEYS[3], 'remaining', total)
for name, quantity in pairs(products) do
    redis.call('HSET', KEYS[3], 'stock:' .. name, quantity)
    for i=1,quantity do
        redis.call('RPUSH', 'game:stock:' .. name, ARGV[5])
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

BUY_FOOD = """
local balance = tonumber(redis.call('GET', KEYS[1]) or '0')
local energy = tonumber(redis.call('GET', KEYS[2]) or '0')
if balance < tonumber(ARGV[1]) then return {-1, ''} end
if energy >= tonumber(ARGV[2]) then return {-2, ''} end
local item = redis.call('LINDEX', KEYS[3], 0)
if not item then return {-3, ''} end
local seller, slot = string.match(item, '^([0-9a-f]+):([0-9]+)$')
if not seller or string.len(seller) ~= 32 then return {-4, ''} end
local plot_key = 'game:plot:' .. seller .. ':' .. slot
local remaining = tonumber(redis.call('HGET', plot_key, 'remaining') or '0')
if remaining > 0 then
    if tonumber(redis.call('HGET', plot_key, 'stock:' .. ARGV[3]) or '0') < 1 then
        return {-4, ''}
    end
else
    -- Compatibility with plots produced by the previous draft implementation.
    if redis.call('HGET', plot_key, 'product') ~= ARGV[3] or
       tonumber(redis.call('HGET', plot_key, 'qty') or '0') < 1 then
        return {-4, ''}
    end
end
redis.call('LPOP', KEYS[3])
redis.call('DECRBY', KEYS[1], ARGV[1])
redis.call('INCRBY', 'game:coins:' .. seller, ARGV[1])
redis.call('SET', KEYS[2], math.min(tonumber(ARGV[2]), energy + tonumber(ARGV[4])))
if remaining > 0 then
    redis.call('HINCRBY', plot_key, 'stock:' .. ARGV[3], -1)
    if redis.call('HINCRBY', plot_key, 'remaining', -1) == 0 then
        redis.call('DEL', plot_key)
    end
elseif redis.call('HINCRBY', plot_key, 'qty', -1) == 0 then
    redis.call('DEL', plot_key)
end
return {1, seller}
"""

RECOVER = """
local current = tonumber(redis.call('GET', KEYS[1]) or '0')
if current >= tonumber(ARGV[1]) then return -1 end
local value = math.min(tonumber(ARGV[1]), current + tonumber(ARGV[2]))
redis.call('SET', KEYS[1], value)
return value
"""

PREPARE_SOIL = """
local coins = tonumber(redis.call('GET', KEYS[1]) or '0')
local soil = tonumber(redis.call('GET', KEYS[2]) or '0')
if soil >= tonumber(ARGV[2]) then return -1 end
if coins < tonumber(ARGV[1]) then return -2 end
redis.call('DECRBY', KEYS[1], ARGV[1])
local value = math.min(tonumber(ARGV[2]), soil + tonumber(ARGV[3]))
redis.call('SET', KEYS[2], value)
return value
"""


def recover_basic(red, owner, kind):
    if kind not in ("farmer", "citizen"):
        raise ValueError("Unknown recovery")
    initialize_player(red, owner)
    resource = "game:soil:" if kind == "farmer" else "game:energy:"
    amount = int(red.register_script(RECOVER)(
        keys=[resource + owner], args=[BASIC_RECOVERY, BASIC_RECOVERY]))
    if amount < 0:
        raise ValueError("Basic recovery is available only below 10")
    return {"resource": "soil_health" if kind == "farmer" else "energy",
            "value": amount}


def prepare_soil(red, owner):
    initialize_player(red, owner)
    value = int(red.register_script(PREPARE_SOIL)(
        keys=["game:coins:" + owner, "game:soil:" + owner],
        args=[SOIL_CARE_COST, 100, SOIL_CARE_GAIN]))
    if value == -1:
        raise ValueError("Soil health is already full")
    if value == -2:
        raise ValueError("Not enough coins to prepare soil")
    return {"soil_health": value, "cost": SOIL_CARE_COST}


def harvest_products(level, pattern, product):
    if level != 3:
        return {product: LEVEL_REWARD[level]}
    return {name: pattern.count(name) for name in PRODUCTS if name in pattern}



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
    red.setnx("game:soil:" + owner, INITIAL_SOIL_HEALTH)


def market(red):
    return {product: red.llen("game:stock:" + product) for product in PRODUCTS}


def state(red, owner):
    initialize_player(red, owner)
    plots = []
    for index in range(PLOTS):
        values = red.hgetall(_plot(owner, index))
        amounts = {
            name: int(values.get(("stock:" + name).encode()) or
                      values.get("stock:" + name) or 0)
            for name in PRODUCTS
        } if values else {}
        legacy_product = _text(values.get(b"product") or values.get("product")) if values else None
        if legacy_product:
            amounts[legacy_product] = int(values.get(b"qty") or values.get("qty") or 0)
        plots.append({
            "index": index,
            "product": legacy_product or ("mixed" if sum(amounts.values()) else None),
            "qty": sum(amounts.values()),
            "products": {name: qty for name, qty in amounts.items() if qty > 0},
        })
    return {
        "coins": int(red.get("game:coins:" + owner) or 0),
        "energy": int(red.get("game:energy:" + owner) or 0),
        "plots": plots,
        "soil_health": int(red.get("game:soil:" + owner) or 0),
    }


def start(red, owner, kind, level, product=None, plot=None):
    if kind not in ("farmer", "citizen"):
        raise ValueError("Unknown activity")
    if type(level) is not int or level not in LEVEL_REWARD:
        raise ValueError("Invalid level")
    if kind == "farmer":
        if type(plot) is not int or plot not in range(PLOTS):
            raise ValueError("Choose an available plot")
        initialize_player(red, owner)
        if int(red.get("game:soil:" + owner) or 0) < SOIL_COST[level]:
            raise ValueError("Not enough soil health. Care for the land.")
        if red.exists(_plot(owner, plot)):
            raise ValueError("This plot is occupied until its food is sold")
        public, expected = create_farm(level, product)
        public["plot"] = plot
    else:
        initialize_player(red, owner)
        if int(red.get("game:energy:" + owner)) < ENERGY_COST:
            raise ValueError("Not enough energy. Buy food to recover.")
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
        product, plot = public["product"], public["plot"]
        level = public["level"]
        products = harvest_products(level, data["expected"], product)
        count = sum(products.values())
        outcome = int(red.register_script(FINISH_FARM)(
            keys=[_challenge(challenge_id), active, _plot(owner, plot),
                  "game:soil:" + owner],
            args=[raw, challenge_id, SOIL_COST[level], json.dumps(products),
                  "{}:{}".format(owner, plot)],
        ))
        if outcome == -1:
            raise ValueError("Plot occupied; choose a free plot")
        if outcome == -2:
            raise ValueError("Not enough soil health")
        reward = {"product": product, "qty": count, "products": products,
                  "soil_cost": SOIL_COST[level]}
    else:
        outcome = int(red.register_script(FINISH_WORK)(
            keys=[_challenge(challenge_id), active,
                  "game:energy:" + owner, "game:coins:" + owner],
            args=[raw, challenge_id, ENERGY_COST, LEVEL_REWARD[public["level"]] * 5],
        ))
        if outcome == -2:
            raise ValueError("Not enough energy")
        reward = {"coins": LEVEL_REWARD[public["level"]] * 5}
    if outcome != 1:
        raise ValueError("Challenge expired or already completed")
    return {"kind": kind, "reward": reward}


def buy(red, owner, product):
    if product not in PRODUCTS:
        raise ValueError("Unknown ingredient")
    initialize_player(red, owner)
    code, seller = red.register_script(BUY_FOOD)(
        keys=["game:coins:" + owner, "game:energy:" + owner,
              "game:stock:" + product],
        args=[FOOD_PRICE, MAX_ENERGY, product, FOOD_ENERGY],
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
