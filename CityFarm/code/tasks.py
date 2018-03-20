#import names
import redis
from celery import Celery

app = Celery('tasks', broker='pyamqp://guest@rabbitmq//')

r = redis.StrictRedis(host='redis', port=6379, db=0)

""" farmer planting """
@app.task
def plant(what):
	r.incr(what)

""" citizen eating """
@app.task
def eat(what):
	r.decr(what)