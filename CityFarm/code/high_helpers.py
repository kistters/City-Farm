
def decr_resource_if_available(red, key, min_limit=0):
    """
    Controls the TPT (Transactions per time) for a given key. Useful when you need to respect some APIs rate limits,
    for instance. Better than using default celery rate_limit in cases where you have more than one worker machine
    running celery.
    :param key:
    :param min_limit: 
    :return:
    """

    # Lua script which does the controlling work:
    script = "\
    local current_value, current_value_int, min_limit \
    current_value = redis.call('GET', KEYS[1]) \
    min_limit = tonumber(ARGV[1]) \
    if current_value then \
        current_value_int = tonumber(current_value) \
    end \
    if current_value_int > min_limit then \
    redis.call('decrby', KEYS[1], 1) \
    return 1 \
    else \
        return 0 \
    end \
    "
    is_rate_okay = red.register_script(script)

    return bool(is_rate_okay(keys=[key], args=[min_limit]))

