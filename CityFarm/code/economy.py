"""Economia do City-Farm: desafios, saldos e transações atômicas no Redis.

Funções Python expressam as regras; Lua é usado apenas onde múltiplas
chaves precisam mudar de forma indivisível (produção, pagamento e compra).
O identificador casual de jogador NÃO autentica o usuário.
"""
import json
import secrets
import time

from products import FOOD, LEGACY_PRODUCTS
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

# Um único estoque "food": cada unidade guarda somente o ID do Farmer.
# Não há limite por terreno ou por lote; Saúde do Solo limita a colheita.
FINISH_FARM = """
if redis.call('GET', KEYS[1]) ~= ARGV[1] then return 0 end
if redis.call('GET', KEYS[2]) ~= ARGV[2] then return 0 end
if tonumber(redis.call('GET', KEYS[3]) or '0') < tonumber(ARGV[3]) then return -2 end
redis.call('DEL', KEYS[1], KEYS[2])
redis.call('DECRBY', KEYS[3], ARGV[3])
for i = 1, tonumber(ARGV[4]) do
    redis.call('RPUSH', KEYS[4], ARGV[5])
end
redis.call('HINCRBY', KEYS[5], 'food_produced', ARGV[4])
return 1
"""

# Cancelamento invalida o desafio e libera o próximo início numa única operação.
CANCEL_CHALLENGE = """
if redis.call('GET', KEYS[1]) ~= ARGV[1] then return 0 end
if redis.call('GET', KEYS[2]) ~= ARGV[2] then return 0 end
redis.call('DEL', KEYS[1], KEYS[2])
return 1
"""

FINISH_WORK = """
if redis.call('GET', KEYS[1]) ~= ARGV[1] then return 0 end
if redis.call('GET', KEYS[2]) ~= ARGV[2] then return 0 end
if tonumber(redis.call('GET', KEYS[3]) or '0') < tonumber(ARGV[3]) then return -2 end
redis.call('DEL', KEYS[1], KEYS[2])
redis.call('DECRBY', KEYS[3], ARGV[3])
redis.call('INCRBY', KEYS[4], ARGV[4])
redis.call('HINCRBY', KEYS[5], 'coins_earned_work', ARGV[4])
return 1
"""

# Um só item econômico: Food. Consumir primeiro o estoque novo e depois os
# estoques antigos preservados no Redis, mantendo o dono original das unidades.
BUY_FOOD = """
local coins = tonumber(redis.call('GET', KEYS[1]) or '0')
local energy = tonumber(redis.call('GET', KEYS[2]) or '0')
if coins < tonumber(ARGV[1]) then return {-1, ''} end
if energy >= tonumber(ARGV[2]) then return {-2, ''} end

local stock_key, item, product
for i = 3, #KEYS - 1 do
    local candidate = redis.call('LINDEX', KEYS[i], 0)
    if candidate then
        stock_key, item, product = KEYS[i], candidate, ARGV[i+1]
        break
    end
end
if not item then return {-3, ''} end

local seller, slot = string.match(item, '^([0-9a-f]+):([0-9]+)$')
if not seller then seller = item end
if not string.match(seller, '^[0-9a-f]+$') or string.len(seller) ~= 32 then
    return {-4, ''}
end

-- Somente para unidades antigas vinculadas a um terreno histórico.
local legacy, previous, field, legacy_key
if slot then
    legacy_key = 'game:plot:' .. seller .. ':' .. slot
    field = 'crop:' .. product
    local count = tonumber(redis.call('HGET', legacy_key, field) or '0')
    legacy, previous = false, false
    if count == 0 then
        field = 'stock:' .. product
        count = tonumber(redis.call('HGET', legacy_key, field) or '0')
        previous = count > 0
    end
    if count == 0 and redis.call('HGET', legacy_key, 'product') == product then
        count = tonumber(redis.call('HGET', legacy_key, 'qty') or '0')
        legacy = true
    end
    if count < 1 then return {-4, ''} end
end

redis.call('LPOP', stock_key)
redis.call('DECRBY', KEYS[1], ARGV[1])
redis.call('INCRBY', 'game:coins:' .. seller, ARGV[1])
redis.call('SET', KEYS[2], math.min(tonumber(ARGV[2]), energy + tonumber(ARGV[3])))

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
redis.call('HINCRBY', KEYS[#KEYS], 'food_eaten', 1)
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
redis.call('HINCRBY', KEYS[3], 'coins_spent_soil', ARGV[1])
return renewed
"""


def _text(value):
    return value.decode("utf-8") if isinstance(value, bytes) else value


def _active(owner, kind):
    return "game:active:{}:{}".format(owner, kind)


def _challenge(challenge_id):
    return "game:challenge:" + challenge_id

def _stats(owner):
    return "game:stats:" + owner


def register_character(red, owner, name, role):
    """Persiste o personagem pelo ID, independentemente da conexão WebSocket."""
    if role not in ("farmer", "citizen"):
        raise ValueError("Invalid character role")
    pipe = red.pipeline()
    pipe.hset("game:character:" + owner, mapping={"name": name, "role": role})
    pipe.sadd("game:characters", owner)
    pipe.execute()


def characters(red):
    """Acumulados por personagem, ordenados para o painel do jogo."""
    owners = red.smembers("game:characters")
    if not owners:
        return []
    pipe = red.pipeline()
    for owner in owners:
        owner = _text(owner)
        pipe.hgetall("game:character:" + owner)
        pipe.hgetall(_stats(owner))
    values = pipe.execute()
    result = []
    for index, owner in enumerate(owners):
        profile, counts = values[2 * index:2 * index + 2]
        if not profile:
            continue
        profile = {_text(key): _text(value) for key, value in profile.items()}
        counts = {_text(key): int(value) for key, value in counts.items()}
        result.append({
            "id": _text(owner),
            "name": profile.get("name", ""),
            "role": profile.get("role", ""),
            "food_produced": counts.get("food_produced", 0),
            "food_eaten": counts.get("food_eaten", 0),
            "coins_earned_work": counts.get("coins_earned_work", 0),
            "coins_spent_soil": counts.get("coins_spent_soil", 0),
        })
    return sorted(result, key=lambda character: (
        character["role"], character["name"].casefold(), character["id"]))



def initialize_player(red, owner):
    red.setnx("game:energy:" + owner, INITIAL_ENERGY)
    # Migra o saldo de solo da versão #22 sem sobrescrever jogadores já migrados.
    previous_soil = red.get("game:soil:" + owner)
    red.setnx("game:soil_health:" + owner,
              int(previous_soil) if previous_soil is not None else INITIAL_SOIL_HEALTH)


def market(red):
    """Um único número de Food, incluindo alimentos das versões anteriores."""
    stock = (FOOD,) + LEGACY_PRODUCTS
    pipe = red.pipeline()
    for product in stock:
        pipe.llen("game:stock:" + product)
    return {FOOD: sum(pipe.execute())}


def state(red, owner):
    initialize_player(red, owner)
    return {
        "coins": int(red.get("game:coins:" + owner) or 0),
        "energy": int(red.get("game:energy:" + owner) or 0),
        "soil_health": int(red.get("game:soil_health:" + owner) or 0),
    }


def start(red, owner, kind, level):
    if kind not in ("farmer", "citizen"):
        raise ValueError("Unknown activity")
    if type(level) is not int or level not in WORK_REWARDS:
        raise ValueError("Invalid level")
    initialize_player(red, owner)
    if kind == "farmer":
        if int(red.get("game:soil_health:" + owner)) < FARM_LEVELS[level]["soil_cost"]:
            raise ValueError("Soil health too low. Care for the soil first.")
        public, expected = create_farm(level)
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
        # Os desenhos diferenciam os puzzles, não os itens produzidos.
        quantity = FARM_LEVELS[public["level"]]["production"]
        outcome = int(red.register_script(FINISH_FARM)(
            keys=[_challenge(challenge_id), active, "game:soil_health:" + owner,
                  "game:stock:" + FOOD, _stats(owner)],
            args=[raw, challenge_id, cost, quantity, owner],
        ))
        if outcome == -2:
            raise ValueError("Not enough soil health")
        reward = {"qty": quantity, "soil_cost": cost}
    else:
        coins = WORK_REWARDS[public["level"]]
        outcome = int(red.register_script(FINISH_WORK)(
            keys=[_challenge(challenge_id), active,
                  "game:energy:" + owner, "game:coins:" + owner,
                  _stats(owner)],
            args=[raw, challenge_id, ENERGY_COST, coins],
        ))
        if outcome == -2:
            raise ValueError("Not enough energy")
        reward = {"coins": coins}
    if outcome != 1:
        raise ValueError("Challenge expired or already completed")
    return {"kind": kind, "reward": reward}


def cancel_challenge(red, owner, challenge_id):
    """Descarta um desafio não concluído, sem recompensa ou gasto de recursos."""
    if not isinstance(challenge_id, str) or len(challenge_id) != 32:
        raise ValueError("Invalid challenge")
    key = _challenge(challenge_id)
    raw = red.get(key)
    if not raw:
        raise ValueError("Challenge expired or already completed")
    challenge = json.loads(raw)
    if challenge["owner"] != owner:
        raise ValueError("Challenge belongs to another player")
    if challenge["public"]["kind"] != "farmer":
        raise ValueError("Only Farmer challenges can be cancelled here")
    result = int(red.register_script(CANCEL_CHALLENGE)(
        keys=[key, _active(owner, challenge["public"]["kind"])],
        args=[raw, challenge_id],
    ))
    if result != 1:
        raise ValueError("Challenge expired or already completed")
    return {"id": challenge_id}


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
        keys=["game:coins:" + owner, "game:soil_health:" + owner, _stats(owner)],
        args=[SOIL_PREPARE_COST, MAX_RESOURCE, SOIL_PREPARE_RECOVERY],
    ))
    if result == -1:
        raise ValueError("Soil health is already full")
    if result == -2:
        raise ValueError("Not enough coins to prepare soil")
    return {"soil_health": result, "cost": SOIL_PREPARE_COST}


def buy(red, owner):
    """Compra uma unidade genérica de Food de qualquer Farmer com estoque."""
    initialize_player(red, owner)
    products = (FOOD,) + LEGACY_PRODUCTS
    keys = ["game:coins:" + owner, "game:energy:" + owner]
    keys += ["game:stock:" + product for product in products]
    keys.append(_stats(owner))
    code, seller = red.register_script(BUY_FOOD)(
        keys=keys,
        args=[FOOD_PRICE, MAX_RESOURCE, FOOD_ENERGY, *products],
    )
    code = int(code)
    if code != 1:
        raise ValueError({
            -1: "Not enough coins",
            -2: "Energy is already full",
            -3: "Food out of stock",
            -4: "Stock needs reconciliation",
        }.get(code, "Purchase failed"))
    return {"product": FOOD, "price": FOOD_PRICE, "seller": _text(seller)}
