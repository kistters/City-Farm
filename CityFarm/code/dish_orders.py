"""Pedidos de pratos: alocação atômica de todos os ingredientes, sem polling.

Cada prato só é preparado quando há estoque para a receita completa.
As demandas ficam visíveis na feira até a preparação.
"""
from dishes import DISHES

QUEUE = "dish:pending:ids"

ENQUEUE = """
if redis.call('EXISTS', KEYS[1]) == 1 then return 0 end
redis.call('SET', KEYS[1], ARGV[1])
redis.call('RPUSH', KEYS[2], ARGV[2])
redis.call('INCR', KEYS[3])
for i=4,#KEYS do
    redis.call('INCRBY', KEYS[i], tonumber(ARGV[i-1]))
end
return 1
"""

FULFILL = """
if redis.call('GET', KEYS[1]) ~= ARGV[1] then return 0 end
local count = (#KEYS - 3) / 3
for i=1,count do
    local stock = KEYS[3*i+1]
    if tonumber(redis.call('GET', stock) or '0') < tonumber(ARGV[i+2]) then
        return 0
    end
end
for i=1,count do
    local stock = KEYS[3*i+1]
    local items = KEYS[3*i+2]
    local pending = KEYS[3*i+3]
    local needed = tonumber(ARGV[i+2])
    redis.call('DECRBY', stock, needed)
    for j=1,math.min(needed, redis.call('LLEN', items)) do
        redis.call('RPOP', items)
    end
    redis.call('DECRBY', pending, needed)
end
redis.call('DEL', KEYS[1])
redis.call('LREM', KEYS[2], 1, ARGV[2])
redis.call('DECR', KEYS[3])
return 1
"""


def enqueue_dish(red, order_id, dish_id):
    recipe = DISHES[dish_id]["ingredients"]
    script = red.register_script(ENQUEUE)
    keys = [
        "dish:pending:" + order_id, QUEUE, "dish:waiting:" + dish_id,
    ] + ["eat:waiting:" + product for product in recipe]
    args = [dish_id, order_id] + list(recipe.values())
    return bool(script(keys=keys, args=args))


def fulfill_pending_dishes(red, limit=200):
    """Called after ordering or a validated harvest; Lua serializes fulfillment."""
    fulfilled = 0
    for order_id in red.lrange(QUEUE, 0, limit - 1):
        order_id = order_id.decode() if isinstance(order_id, bytes) else order_id
        raw_dish = red.get("dish:pending:" + order_id)
        if not raw_dish:
            # A concurrent worker may already have settled this order.
            continue
        dish_id = raw_dish.decode() if isinstance(raw_dish, bytes) else raw_dish
        if dish_id not in DISHES:
            continue
        recipe = DISHES[dish_id]["ingredients"]
        keys = ["dish:pending:" + order_id, QUEUE, "dish:waiting:" + dish_id]
        for product in recipe:
            keys.extend([product, "products:" + product, "eat:waiting:" + product])
        args = [dish_id, order_id] + list(recipe.values())
        if red.register_script(FULFILL)(keys=keys, args=args):
            fulfilled += 1
    return fulfilled
