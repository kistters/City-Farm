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


def valid_proof(challenge, nonce, difficulty=3):
    digest = hashlib.sha256("{}:{}".format(challenge, nonce).encode("utf-8")).hexdigest()
    return digest.startswith("0" * difficulty)


@app.task
def verify_tomato_proof(challenge_id, nonce, farmer):
    if not isinstance(challenge_id, str) or len(challenge_id) != 32:
        return False
    if type(nonce) is not int or not 0 <= nonce <= 10000000:
        return False
    key = "pow:challenge:" + challenge_id
    raw = r.get(key)
    if not raw:
        return False
    challenge = raw.decode("utf-8")
    if not challenge.startswith("cityfarm:v1:" + challenge_id + ":tomato:"):
        return False
    if not valid_proof(challenge, nonce):
        return False
    product = json.dumps({"id": str(uuid.uuid4()), "name": "tomato", "farmer": farmer})
    accepted = ACCEPT_PROOF(keys=[key, "products:tomato", "tomato"], args=[challenge, product])
    if accepted:
        notify()
    return bool(accepted)
