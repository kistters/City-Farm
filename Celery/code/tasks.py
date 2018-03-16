#import names
import redis
from celery import Celery

app = Celery('tasks', broker='pyamqp://guest@rabbitmq//')

r = redis.StrictRedis(host='redis', port=6379, db=0)

def register(name):
	r.incr(name)

def unregister(name):
	r.decr(name)

@app.task
def plantarMilho():
	for idx in range(1,100):
		#name = names.get_full_name()
		register('milho')

@app.task
def plantarTrigo():
	for idx in range(1,100):
		#name = names.get_full_name()
		register('trigo')

@app.task
def comerMilho():
	for idx in range(1,100):
		unregister('milho')

@app.task
def comerTrigo():
	for idx in range(1,100):
		unregister('trigo')


# poderia ser um container com redis
# serializer='json'
# celery -A tasks worker --loglevel=info -Q trigo