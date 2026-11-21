from celery import Celery
from eat_orders import LUA_DRAIN, enqueue_eat, migrate_legacy_order
import os
import hashlib
import json
import uuid
import redis, requests
from products import PRODUCT_DIFFICULTIES
from dish_orders import fulfill_pending_dishes

app = Celery('tasks', broker=os.environ.get('CELERY_BROKER_URL', 'amqp://cityfarm:cityfarm_dev@rabbitmq:5672//'))

r = redis.StrictRedis(host='redis', port=6379, db=0)

def notify():
	requests.get('http://websocket:8888/update', timeout=3)

""" Compatibility: drain retries already enqueued by previous releases.

Old Celery tasks are converted into durable Redis orders once. New requests
do not schedule tasks at all; the browser WebSocket writes to Redis directly.
"""
@app.task(bind=True, max_retries=0)
def eat(self, what, request_id=None):
    if what not in PRODUCT_DIFFICULTIES:
        return False
    if request_id:
        migrated = migrate_legacy_order(r, what, request_id)
    else:
        # Before the request_id release, tasks had no durable order marker.
        # Celery retries keep the same task ID; this deduplicates migrations.
        migrated = enqueue_eat(r, what, "legacy-" + str(self.request.id or uuid.uuid4()))["created"]
    notify()
    return bool(migrated)


# Atomic proof consumption + harvest + FIFO eat fulfillment.
# The dashboard sees only committed Redis state, never half a production.
ACCEPT_PROOF_SCRIPT = LUA_DRAIN + """
if redis.call('GET', KEYS[1]) ~= ARGV[1] then
    return 0
end
redis.call('DEL', KEYS[1])
redis.call('LPUSH', KEYS[2], ARGV[2])
redis.call('INCR', KEYS[3])
drain_orders(KEYS[3], KEYS[2], KEYS[4], KEYS[5], KEYS[6], ARGV[3])
return 1
"""
ACCEPT_PROOF = r.register_script(ACCEPT_PROOF_SCRIPT)


def proof_digest(challenge, nonce):
    return hashlib.sha256("{}:{}".format(challenge, nonce).encode("utf-8")).hexdigest()


def valid_proof(challenge, nonce, difficulty=3):
    return proof_digest(challenge, nonce).startswith("0" * difficulty)


def record_proof(challenge_id, nonce, farmer, digest, valid, reason, product):
    from datetime import datetime, timezone
    event = json.dumps({
        "id": challenge_id,
        "product": product,
        "farmer": farmer["name"] if isinstance(farmer, dict) else str(farmer),
        "farmer_id": farmer.get("id") if isinstance(farmer, dict) else None,
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
                    registered_farmer != farmer or
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
                            "id": str(uuid.uuid4()), "name": product,
                            "farmer": farmer["id"], "farmer_name": farmer["name"],
                        })
                        accepted = bool(ACCEPT_PROOF(
                            keys=[
                                key, "products:" + product, product,
                                "eat:queue:" + product, "eat:waiting:" + product,
                                "eat:fulfilled:" + product,
                            ],
                            args=[raw, item, product],
                        ))
                        reason = "accepted" if accepted else "already_used"
        else:
            reason = "expired_or_used"

    if accepted:
        fulfill_pending_dishes(r)
    record_proof(challenge_id, nonce, farmer, digest, accepted, reason, product)
    return accepted
