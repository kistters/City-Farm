from celery import Celery

app = Celery('tasks', broker='pyamqp://guest@localhost//')

@app.task
def reverse(text):
    return text[::-1]