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

# A lista Redis do produto é o estoque. Cada unidade guarda apenas o ID do Farmer.
# Não há terreno, slot nem capacidade máxima; Saúde do Solo limita a colheita.
FINISH_FARM = """
if redis.call('GET', KEYS[1]) ~= ARGV[1] then return 0 end
if redis.call('GET', KEYS[2]) ~= ARGV[2] then return 0 end
if tonumber(redis.call('GET', KEYS[3]) or '0') < tonumber(ARGV[3]) then return -2 end
local crops = cjson.decode(ARGV[4])
redis.call('DEL', KEYS[1], KEYS[2])
redis.call('DECRBY', KEYS[3], ARGV[3])
for product, count in pairs(crops) do
    for i = 1, count do
        redis.call('RPUSH', 'game:stock:' .. product, ARGV[5])
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

# As novas unidades carregam apenas o ID do vendedor. Itens antigos com
# ID:slot continuam vendáveis, mas não restringem novas plantações.
BUY_FOOD = """
local coins = tonumber(redis.call('GET', KEYS[1]) or '0')
local energy = tonumber(redis.call('GET', KEYS[2]) or '0')
if coins < tonumber(ARGV[1]) then return {-1, ''} end
if energy >= tonumber(ARGV[2]) then return {-2, ''} end
local item = redis.call('LINDEX', KEYS[3], 0)
if not item then return {-3, ''} end

local seller, slot = string.match(item, '^([0-9a-f]+):([0-9]+)$')
if not seller then
    seller = item
end
if not string.match(seller, '^[0-9a-f]+$') or string.len(seller) ~= 32 then
    return {-4, ''}
end

local legacy, previous, field, legacy_key
if slot then
    legacy_key = 'game:plot:' .. seller .. ':' .. slot
    field = 'crop:' .. ARGV[3]
    local count = tonumber(redis.call('HGET', legacy_key, field) or '0')
    legacy, previous = false, false
    if count == 0 then
        field = 'stock:' .. ARGV[3]
        count = tonumber(redis.call('HGET', legacy_key, field) or '0')
        previous = count > 0
    end
    if count == 0 and redis.call('HGET', legacy_key, 'product') == ARGV[3] then
        count = tonumber(redis.call('HGET', legacy_key, 'qty') or '0')
        legacy = true
    end
    if count < 1 then return {-4, ''} end
end

redis.call('LPOP', KEYS[3])
redis.call('DECRBY', KEYS[1], ARGV[1])
redis.call('INCRBY', 'game:coins:' .. seller, ARGV[1])
redis.call('SET', KEYS[2], math.min(tonumber(ARGV[2]), energy + tonumber(ARGV[4])))

if slot then
    if legacy then
        if redis.call('HINCRBY', legacy_key, 'qty', -1) == 0 then
            redis.call('DEL', legacy_key)
        end
    elseif previous then
        redis.call('HINCRBY', legacy_key, field, -1)
        if redis.call('HINCRBY', legacy_key, 'remaining', -1) == 0 then
            redis.call('DEL', legacy_key)
        end
    else
        if redis.call('HINCRBY', legacy_key, field, -1) == 0 then
            redis.call('HDEL', legacy_key, field)
            if redis.call('HLEN', legacy_key) == 0 then
                redis.call('DEL', legacy_key)
            end
        end
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


def initialize_player(red, owner):
    red.setnx("game:energy:" + owner, INITIAL_ENERGY)
    # Migra o saldo de solo da versão #22 sem sobrescrever jogadores já migrados.
    previous_soil = red.get("game:soil:" + owner)
    red.setnx("game:soil_health:" + owner,
              int(previous_soil) if previous_soil is not None else INITIAL_SOIL_HEALTH)


def market(red):
    return {product: red.llen("game:stock:" + product) for product in PRODUCTS}


def state(red, owner):
    initialize_player(red, owner)
    return {
        "coins": int(red.get("game:coins:" + owner) or 0),
        "energy": int(red.get("game:energy:" + owner) or 0),
        "soil_health": int(red.get("game:soil_health:" + owner) or 0),
    }


def start(red, owner, kind, level, product=None):
    if kind not in ("farmer", "citizen"):
        raise ValueError("Unknown activity")
    if type(level) is not int or level not in WORK_REWARDS:
        raise ValueError("Invalid level")
    initialize_player(red, owner)
    if kind == "farmer":
        if int(red.get("game:soil_health:" + owner)) < FARM_LEVELS[level]["soil_cost"]:
            raise ValueError("Soil health too low. Care for the soil first.")
        public, expected = create_farm(level, product)
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
        cost = FARM_LEVELS[public["level"]]["soil_cost"]
        # Dificuldade visual (células) e produção são regras distintas.
        # Só na multicultura a colheita corresponde a cada ícone mostrado.
        if public["level"] == 3:
            counts = Counter(crop for crop in data["expected"] if crop)
        else:
            counts = Counter({public["product"]: FARM_LEVELS[public["level"]]["production"]})
        outcome = int(red.register_script(FINISH_FARM)(
            keys=[_challenge(challenge_id), active,
                  "game:soil_health:" + owner],
            args=[raw, challenge_id, cost, json.dumps(counts), owner],
        ))
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
