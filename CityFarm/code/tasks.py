from celery import Celery
from high_helpers import decr_resource_if_available
import os
import hashlib
import json
import uuid
import redis, requests
from products import PRODUCT_DIFFICULTIES

app = Celery('tasks', broker=os.environ.get('CELERY_BROKER_URL', 'amqp://cityfarm:cityfarm_dev@rabbitmq:5672//'))

r = redis.StrictRedis(host='redis', port=6379, db=0)

def notify():
	requests.get('http://websocket:8888/update', timeout=3)

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


def record_proof(challenge_id, nonce, farmer, digest, valid, reason, product):
    from datetime import datetime, timezone
    event = json.dumps({
        "id": challenge_id,
        "product": product,
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
def verify_product_proof(challenge_id, nonce, farmer):
    key = "pow:challenge:" + challenge_id if isinstance(challenge_id, str) else ""
    digest = None
    reason = "invalid_input"
    accepted = False
    product = None

    if isinstance(challenge_id, str) and len(challenge_id) == 32 and type(nonce) is int and 0 <= nonce <= 10000000:
        raw = r.get(key)
        if raw:
            try:
                challenge_data = json.loads(raw)
                challenge = challenge_data["challenge"]
                product = challenge_data["product"]
                difficulty = challenge_data["difficulty"]
                registered_farmer = challenge_data.get("farmer")
            except (ValueError, KeyError, TypeError):
                reason = "invalid_challenge"
            else:
                if (not isinstance(registered_farmer, dict) or
                    not isinstance(registered_farmer.get("name"), str) or
                    registered_farmer.get("name") != farmer or
                    product not in PRODUCT_DIFFICULTIES or
                    type(difficulty) is not int or
                    difficulty != PRODUCT_DIFFICULTIES[product] or
                    not challenge.startswith("cityfarm:v1:{}:{}:".format(challenge_id, product))):
                    reason = "invalid_challenge"
                else:
                    digest = proof_digest(challenge, nonce)
                    if not valid_proof(challenge, nonce, difficulty):
                        reason = "invalid_hash"
                    else:
                        item = json.dumps({
                            "id": str(uuid.uuid4()), "name": product, "farmer": farmer,
                        })
                        accepted = bool(ACCEPT_PROOF(
                            keys=[key, "products:" + product, product],
                            args=[raw, item],
                        ))
                        reason = "accepted" if accepted else "already_used"
        else:
            reason = "expired_or_used"

    record_proof(challenge_id, nonce, farmer, digest, accepted, reason, product)
    return accepted
