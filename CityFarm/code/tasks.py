from rate_limit import decr_resource_if_available
import redis, requests
from celery import Celery

app = Celery('tasks', broker='pyamqp://guest@rabbitmq//')

r = redis.StrictRedis(host='redis', port=6379, db=0)



def updateSocket():
	URL = "http://websocket:8888/update" # set into conf
	r = requests.get(url = URL)

""" farmer planting """
@app.task
def plant(what):
	for x in range(3):
		r.incr(what)

	updateSocket()

""" citizen eating """
#@app.task(bind=True, max_retries=3)
@app.task(bind=True, max_retries=None)
def eat(self, what):
	if not decr_resource_if_available(r, what):
		self.retry(countdown=3)
	else:
		updateSocket()