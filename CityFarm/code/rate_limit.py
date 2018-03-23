
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


####################################
###### How to use it ###############
####################################


# import redis
# r = redis.StrictRedis(host='locahost', port="6379", db=0)

# consumers = 15
# resource_type = "milho"
# initial_amount = 10

# # Setting initial amount for the given resource
# r.set(resource_type, initial_amount)

# # Consuming more than the initial amount
# for consumer in range(consumers):
#     decr_resource_if_available(r, resource_type)

# # Final amount is always zero, never negative. Even tough we run this script in multiple machines at the same time
# final_amount = r.get(resource_type)
# print("Final amount of {} is {}".format(resource_type, final_amount))

