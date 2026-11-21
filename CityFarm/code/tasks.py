from celery import Celery
from high_helpers import decr_resource_if_available
import os
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