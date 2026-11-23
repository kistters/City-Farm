"""Short-lived puzzle payloads; no balances or inventory live in Redis."""
import logging

import redis


CREATE_CHALLENGE = """
if redis.call('EXISTS', KEYS[1]) == 1 then return 0 end
redis.call('SET', KEYS[1], ARGV[1], 'EX', ARGV[3])
redis.call('SET', KEYS[2], ARGV[2], 'EX', ARGV[3])
return 1
"""
CLEAR_CHALLENGE = """
if redis.call('GET', KEYS[1]) ~= ARGV[1] then return 0 end
redis.call('DEL', KEYS[1], KEYS[2])
return 1
"""


class ChallengeRepository:
    def __init__(self, redis_client):
        self.redis = redis_client

    @staticmethod
    def active_key(owner, kind):
        return f"game:active:{owner}:{kind}"

    @staticmethod
    def challenge_key(challenge_id):
        return f"game:challenge:{challenge_id}"

    def load_challenge(self, challenge_id):
        return self.redis.get(self.challenge_key(challenge_id))

    def load_active_challenge(self, owner, kind):
        challenge_id = self.redis.get(self.active_key(owner, kind))
        if isinstance(challenge_id, bytes):
            challenge_id = challenge_id.decode()
        return challenge_id, self.load_challenge(challenge_id) if challenge_id else None

    def remove_stale_active_challenge(self, owner, kind):
        # Compare inside Lua: never delete a replacement created by another request.
        self.redis.eval("""
local id = redis.call('GET', KEYS[1])
if id and redis.call('EXISTS', ARGV[1] .. id) == 0 then
    redis.call('DEL', KEYS[1])
end
""", 1, self.active_key(owner, kind), "game:challenge:")

    def save_new_challenge(self, owner, kind, challenge_id, payload, ttl):
        return bool(self.redis.register_script(CREATE_CHALLENGE)(
            keys=[self.active_key(owner, kind), self.challenge_key(challenge_id)],
            args=[challenge_id, payload, ttl]))

    def clear_completed_challenge(self, owner, kind, challenge_id):
        try:
            self.redis.register_script(CLEAR_CHALLENGE)(
                keys=[self.active_key(owner, kind), self.challenge_key(challenge_id)],
                args=[challenge_id])
        except redis.RedisError:
            # SQL has committed. Its receipt prevents replay; Redis expires naturally.
            logging.exception("Challenge cleanup failed after database commit")
