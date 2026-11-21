from celery import Celery
from high_helpers import decr_resource_if_available
import os
import hashlib
import json
import uuid
import redis, requests

app = Celery('tasks', broker=os.environ.get('CELERY_BROKER_URL', 'amqp://cityfarm:cityfarm_dev@rabbitmq:5672//'))

r = redis.StrictRedis(host='redis', port=6379, db=0)

def notify():
	requests.get('http://websocket:8888/update', timeout=3)

""" farmer planting """
@app.task
def plant(what):
	for x in range(2):
		r.incr(what)

	notify()

""" citizen eating """
#@app.task(bind=True, max_retries=3)
@app.task(bind=True, max_retries=None)
def eat(self, what):
	if not decr_resource_if_available(r, what):
		self.retry(countdown=3)

	notify()

# One browser proof produces one tomato; verification is inexpensive.
# Challenge deletion, product creation and stock increment are atomic.
ACCEPT_PROOF = r.register_script("""
local challenge = redis.call('GET', KEYS[1])
if not challenge or challenge ~= ARGV[1] then
    return 0
end
redis.call('DEL', KEYS[1])
redis.call('LPUSH', KEYS[2], ARGV[2])
redis.call('INCR', KEYS[3])
return 1
""")


def proof_digest(challenge, nonce):
    return hashlib.sha256("{}:{}".format(challenge, nonce).encode("utf-8")).hexdigest()


def valid_proof(challenge, nonce, difficulty=3):
    return proof_digest(challenge, nonce).startswith("0" * difficulty)


def record_proof(challenge_id, nonce, farmer, digest, valid, reason):
    from datetime import datetime, timezone
    event = json.dumps({
        "id": challenge_id,
        "product": "tomato",
        "farmer": farmer,
        "nonce": nonce,
        "hash": digest,
        "valid": valid,
        "reason": reason,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    pipe = r.pipeline()
    pipe.lpush("pow:history", event)
    pipe.ltrim("pow:history", 0, 49)
    pipe.execute()
    notify()


@app.task
def verify_tomato_proof(challenge_id, nonce, farmer):
    key = "pow:challenge:" + challenge_id if isinstance(challenge_id, str) else ""
    digest = None
    reason = "invalid_input"
    accepted = False

    if isinstance(challenge_id, str) and len(challenge_id) == 32 and type(nonce) is int and 0 <= nonce <= 10000000:
        raw = r.get(key)
        if raw:
            challenge = raw.decode("utf-8")
            digest = proof_digest(challenge, nonce)
            if not challenge.startswith("cityfarm:v1:" + challenge_id + ":tomato:"):
                reason = "invalid_challenge"
            elif not valid_proof(challenge, nonce):
                reason = "invalid_hash"
            else:
                product = json.dumps({
                    "id": str(uuid.uuid4()), "name": "tomato", "farmer": farmer,
                })
                accepted = bool(ACCEPT_PROOF(
                    keys=[key, "products:tomato", "tomato"],
                    args=[challenge, product],
                ))
                reason = "accepted" if accepted else "already_used"
        else:
            reason = "expired_or_used"

    record_proof(challenge_id, nonce, farmer, digest, accepted, reason)
    return accepted
