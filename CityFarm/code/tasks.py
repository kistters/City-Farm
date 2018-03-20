#import names
import redis
from celery import Celery

app = Celery('tasks', broker='pyamqp://guest@rabbitmq//')

r = redis.StrictRedis(host='redis', port=6379, db=0)

""" farmer planting """
@app.task
def plant(what):
	for x in range(3):
		r.incr(what)

""" citizen eating """
#@app.task(bind=True, max_retries=3)
@app.task(bind=True, max_retries=None)
def eat(self, what):
	if int(r.get(what).decode('utf8')) > 0:
		r.decr(what)
	else:
		self.retry(countdown=3) 