"""Acesso ao Redis para a economia.

Esta classe concentra nomes de chaves e comandos Redis. Ela não decide se uma
ação é permitida pelo jogo; essa regra fica em :mod:`economy`.
"""
from products import FOOD


# Os scripts garantem que uma transação inteira ocorra no Redis ou não ocorra.
FINISH_FARM = """
if redis.call('GET', KEYS[1]) ~= ARGV[1] then return 0 end
if redis.call('GET', KEYS[2]) ~= ARGV[2] then return 0 end
if tonumber(redis.call('GET', KEYS[3]) or '0') < tonumber(ARGV[3]) then return -2 end
redis.call('DEL', KEYS[1], KEYS[2])
redis.call('DECRBY', KEYS[3], ARGV[3])
for i = 1, tonumber(ARGV[4]) do redis.call('RPUSH', KEYS[4], ARGV[5]) end
redis.call('HINCRBY', KEYS[5], 'food_produced', ARGV[4])
return 1
"""

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

BUY_FOOD = """
local coins = tonumber(redis.call('GET', KEYS[1]) or '0')
local energy = tonumber(redis.call('GET', KEYS[2]) or '0')
if coins < tonumber(ARGV[1]) then return {-1, ''} end
if energy >= tonumber(ARGV[2]) then return {-2, ''} end
local item = redis.call('LINDEX', KEYS[3], 0)
if not item then return {-3, ''} end
local seller = item
if not string.match(seller, '^[0-9a-f]+$') or string.len(seller) ~= 32 then return {-4, ''} end
redis.call('LPOP', KEYS[3])
redis.call('DECRBY', KEYS[1], ARGV[1])
redis.call('INCRBY', 'game:coins:' .. seller, ARGV[1])
redis.call('SET', KEYS[2], math.min(tonumber(ARGV[2]), energy + tonumber(ARGV[3])))
redis.call('HINCRBY', KEYS[#KEYS], 'food_eaten', 1)
return {1, seller}
"""

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


def text(value):
    return value.decode("utf-8") if isinstance(value, bytes) else value


class EconomyRepository:
    """Porta de entrada única para os dados de economia no Redis."""

    def __init__(self, redis_client):
        self.redis = redis_client

    @staticmethod
    def active_key(owner, kind):
        return f"game:active:{owner}:{kind}"

    @staticmethod
    def challenge_key(challenge_id):
        return "game:challenge:" + challenge_id

    @staticmethod
    def stats_key(owner):
        return "game:stats:" + owner

    def initialize_player(self, owner, initial_energy, initial_soil_health):
        self.redis.setnx("game:energy:" + owner, initial_energy)
        previous_soil = self.redis.get("game:soil:" + owner)
        self.redis.setnx("game:soil_health:" + owner,
                         int(previous_soil) if previous_soil is not None else initial_soil_health)

    def load_player_resource_status(self, owner):
        return {
            "coins": int(self.redis.get("game:coins:" + owner) or 0),
            "energy": int(self.redis.get("game:energy:" + owner) or 0),
            "soil_health": int(self.redis.get("game:soil_health:" + owner) or 0),
        }

    def save_player_character(self, owner, name, role):
        pipe = self.redis.pipeline()
        pipe.hset("game:character:" + owner, mapping={"name": name, "role": role})
        pipe.sadd("game:characters", owner)
        pipe.execute()

    def load_character_summaries(self):
        owners = self.redis.smembers("game:characters")
        pipe = self.redis.pipeline()
        for owner in owners:
            owner = text(owner)
            pipe.hgetall("game:character:" + owner)
            pipe.hgetall(self.stats_key(owner))
        return owners, pipe.execute()

    def count_available_food(self):
        return self.redis.llen("game:stock:" + FOOD)

    def load_active_challenge(self, owner, kind):
        challenge_id = text(self.redis.get(self.active_key(owner, kind)))
        return challenge_id, self.load_challenge(challenge_id) if challenge_id else None

    def load_challenge(self, challenge_id):
        return self.redis.get(self.challenge_key(challenge_id))

    def remove_stale_active_challenge(self, owner, kind):
        self.redis.delete(self.active_key(owner, kind))

    def save_new_challenge(self, owner, kind, challenge_id, payload, ttl):
        active = self.active_key(owner, kind)
        if not self.redis.set(active, challenge_id, ex=ttl, nx=True):
            return False
        self.redis.setex(self.challenge_key(challenge_id), ttl, payload)
        return True

    def complete_farming_challenge(self, raw, challenge_id, owner, cost, quantity):
        return int(self.redis.register_script(FINISH_FARM)(
            keys=[self.challenge_key(challenge_id), self.active_key(owner, "farmer"),
                  "game:soil_health:" + owner, "game:stock:" + FOOD, self.stats_key(owner)],
            args=[raw, challenge_id, cost, quantity, owner]))

    def complete_work_challenge(self, raw, challenge_id, owner, cost, coins):
        return int(self.redis.register_script(FINISH_WORK)(
            keys=[self.challenge_key(challenge_id), self.active_key(owner, "citizen"),
                  "game:energy:" + owner, "game:coins:" + owner, self.stats_key(owner)],
            args=[raw, challenge_id, cost, coins]))

    def cancel_active_challenge(self, raw, challenge_id, owner, kind):
        return int(self.redis.register_script(CANCEL_CHALLENGE)(
            keys=[self.challenge_key(challenge_id), self.active_key(owner, kind)],
            args=[raw, challenge_id]))

    def restore_to_minimum(self, key, recovery):
        return int(self.redis.register_script(BASIC_RESTORE)(keys=[key], args=[recovery]))

    def pay_to_prepare_soil(self, owner, cost, maximum, recovery):
        return int(self.redis.register_script(PAID_SOIL_CARE)(
            keys=["game:coins:" + owner, "game:soil_health:" + owner, self.stats_key(owner)],
            args=[cost, maximum, recovery]))

    def purchase_next_food(self, owner, price, maximum_energy, gained_energy):
        keys = ["game:coins:" + owner, "game:energy:" + owner,
                "game:stock:" + FOOD, self.stats_key(owner)]
        code, seller = self.redis.register_script(BUY_FOOD)(
            keys=keys, args=[price, maximum_energy, gained_energy])
        return int(code), text(seller)
