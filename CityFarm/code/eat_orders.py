"""Event-driven single-ingredient orders, persisted as FIFO queues in Redis.

A new order is atomically enqueued and settled if stock is available.
A successful PoW harvest settles waiting orders in the same Lua transaction
that creates the product. No background polling or Celery retry is needed.
"""
from products import PRODUCT_DIFFICULTIES

MAX_PENDING_PER_PRODUCT = 200

# Arguments: stock, product list, FIFO queue, pending counter, fulfilled counter,
# product name. IDs are stored in marker keys (eat:pending:<id>) until fulfilled.
LUA_DRAIN = """
local function drain_orders(stock, items, queue, waiting, fulfilled, product)
    local completed = 0
    while tonumber(redis.call('GET', stock) or '0') > 0 do
        local order_id = redis.call('LPOP', queue)
        if not order_id then break end
        local marker = 'eat:pending:' .. order_id
        if redis.call('GET', marker) == product then
            redis.call('DEL', marker)
            redis.call('DEL', 'eat:queued:' .. order_id)
            -- Keep a bounded idempotency tombstone for old Celery retries.
            redis.call('SETEX', 'eat:completed:' .. order_id, 604800, '1')
            redis.call('DECR', stock)
            if redis.call('LLEN', items) > 0 then
                redis.call('RPOP', items)
            end
            if tonumber(redis.call('GET', waiting) or '0') > 0 then
                redis.call('DECR', waiting)
            end
            redis.call('INCR', fulfilled)
            completed = completed + 1
        end
    end
    return completed
end
"""

ENQUEUE = LUA_DRAIN + """
local completed = drain_orders(KEYS[1], KEYS[2], KEYS[3], KEYS[4], KEYS[5], ARGV[2])
if redis.call('EXISTS', KEYS[6]) == 1 or
   redis.call('EXISTS', 'eat:completed:' .. ARGV[1]) == 1 then
    return {-2, 0}
end
if redis.call('LLEN', KEYS[3]) >= tonumber(ARGV[3]) then return {-1, completed} end
redis.call('SET', KEYS[6], ARGV[2])
redis.call('SET', KEYS[7], '1')
redis.call('RPUSH', KEYS[3], ARGV[1])
redis.call('INCR', KEYS[4])
drain_orders(KEYS[1], KEYS[2], KEYS[3], KEYS[4], KEYS[5], ARGV[2])
-- Report only whether THIS order was settled; older orders may also finish.
return {1, redis.call('EXISTS', KEYS[6]) == 0 and 1 or 0}
"""

# Previous versions created eat:pending:<id> and incremented the pending counter
# before dispatching Celery tasks. Requeue those markers only once; do not count
# them a second time. The marker is deleted only once the order is consumed.
MIGRATE = LUA_DRAIN + """
if redis.call('GET', KEYS[6]) ~= ARGV[2] then return 0 end
if redis.call('SETNX', KEYS[7], '1') == 0 then return 0 end
redis.call('RPUSH', KEYS[3], ARGV[1])
drain_orders(KEYS[1], KEYS[2], KEYS[3], KEYS[4], KEYS[5], ARGV[2])
return 1
"""

SETTLE = LUA_DRAIN + """
return drain_orders(KEYS[1], KEYS[2], KEYS[3], KEYS[4], KEYS[5], ARGV[1])
"""


def order_keys(product, order_id=None):
    keys = [
        product, "products:" + product,
        "eat:queue:" + product, "eat:waiting:" + product,
        "eat:fulfilled:" + product,
    ]
    if order_id is not None:
        keys.extend(["eat:pending:" + order_id, "eat:queued:" + order_id])
    return keys


def enqueue_eat(red, product, order_id):
    if product not in PRODUCT_DIFFICULTIES:
        raise ValueError("Unknown product")
    result = red.register_script(ENQUEUE)(
        keys=order_keys(product, order_id),
        args=[order_id, product, MAX_PENDING_PER_PRODUCT],
    )
    code = int(result[0])
    if code == -1:
        raise ValueError("Too many pending orders for {}".format(product))
    return {"created": code == 1, "fulfilled": int(result[1]) == 1}


def settle_eat(red, product):
    if product not in PRODUCT_DIFFICULTIES:
        raise ValueError("Unknown product")
    return int(red.register_script(SETTLE)(
        keys=order_keys(product), args=[product],
    ))


def migrate_legacy_order(red, product, order_id):
    if product not in PRODUCT_DIFFICULTIES:
        return False
    result = red.register_script(MIGRATE)(
        keys=order_keys(product, order_id),
        args=[order_id, product],
    )
    return bool(result)


def recover_pending_orders(red):
    """Idempotently migrate old markers, then settle queued orders at startup.

    Also handles a process crash after a previous harvest but before an older
    order was settled. Existing queue entries and counters are not duplicated.
    """
    migrated = 0
    for key in red.scan_iter(match="eat:pending:*"):
        key = key.decode("utf-8") if isinstance(key, bytes) else key
        order_id = key[len("eat:pending:"):]
        product = red.get(key)
        if not product:
            continue
        product = product.decode("utf-8") if isinstance(product, bytes) else product
        if product in PRODUCT_DIFFICULTIES:
            migrated += int(migrate_legacy_order(red, product, order_id))
    for product in PRODUCT_DIFFICULTIES:
        settle_eat(red, product)
    return migrated

# One-time compatibility for orders created before Dish support was removed.
# This catalog exists ONLY to compensate outstanding Redis demand counters.
RETIRED_RECIPES = {
    "rice_beans_beef": {"rice": 1, "beans": 1, "beef": 1},
    "omelette": {"eggs": 2, "tomato": 1},
    "chicken_potatoes": {"chicken_meat": 1, "potato": 2},
    "fruit_salad": {"orange": 1, "banana": 1, "apple": 1},
    "fish_rice": {"fish": 1, "rice": 1},
}

RETIRE_DISH = """
local dish = redis.call('GET', KEYS[1])
if not dish then
    redis.call('LREM', KEYS[2], 1, ARGV[1])
    return 0
end
if dish ~= ARGV[2] then return 0 end
for i=4,#KEYS do
    local current = tonumber(redis.call('GET', KEYS[i]) or '0')
    redis.call('SET', KEYS[i], math.max(0, current - tonumber(ARGV[i-1])))
end
local waiting = tonumber(redis.call('GET', KEYS[3]) or '0')
redis.call('SET', KEYS[3], math.max(0, waiting - 1))
redis.call('DEL', KEYS[1])
redis.call('LREM', KEYS[2], 1, ARGV[1])
return 1
"""


def retire_legacy_dishes(red):
    """Cancel old dish orders and adjust demand, preserving individual eat orders."""
    removed = 0
    for raw_id in red.lrange("dish:pending:ids", 0, -1):
        order_id = raw_id.decode() if isinstance(raw_id, bytes) else raw_id
        raw_dish = red.get("dish:pending:" + order_id)
        if raw_dish is None:
            red.lrem("dish:pending:ids", 1, order_id)
            continue
        dish_id = raw_dish.decode() if isinstance(raw_dish, bytes) else raw_dish
        recipe = RETIRED_RECIPES.get(dish_id)
        if recipe is None:
            # Leave unknown orders untouched; don't guess how to compensate.
            continue
        keys = [
            "dish:pending:" + order_id,
            "dish:pending:ids",
            "dish:waiting:" + dish_id,
        ] + ["eat:waiting:" + ingredient for ingredient in recipe]
        args = [order_id, dish_id] + list(recipe.values())
        removed += int(red.register_script(RETIRE_DISH)(keys=keys, args=args))
    return removed
