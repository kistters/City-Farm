def decr_resource_if_available(red, key, min_limit=0, request_id=None):
    """Consume one item and settle its pending eat order atomically in Redis.

    Older eat tasks without request_id continue to work without changing
    the pending counters of newer orders.
    """
    script = """
    local current = tonumber(redis.call('GET', KEYS[1]) or '0')
    if current <= tonumber(ARGV[1]) then
        return 0
    end
    redis.call('DECR', KEYS[1])
    if redis.call('LLEN', KEYS[2]) > 0 then
        redis.call('RPOP', KEYS[2])
    end
    if KEYS[3] ~= 'eat:pending:legacy' and redis.call('GET', KEYS[3]) == ARGV[2] then
        redis.call('DEL', KEYS[3])
        if tonumber(redis.call('GET', KEYS[4]) or '0') > 0 then
            redis.call('DECR', KEYS[4])
        end
    end
    return 1
    """
    consume = red.register_script(script)
    marker = "eat:pending:" + request_id if request_id else "eat:pending:legacy"
    return bool(consume(
        keys=[key, "products:" + key, marker, "eat:waiting:" + key],
        args=[min_limit, key],
    ))
