#!/usr/bin/env python
from flask import Flask, request, render_template, redirect

import pika

app = Flask(__name__)

@app.route('/send/<book>')

def send_message(book):
	connection = pika.BlockingConnection(pika.ConnectionParameters(host='rabbitmq'))
	channel = connection.channel()
	channel.queue_declare(queue='hello')
	channel.basic_publish(exchange='',
                      routing_key='hello',
                      body=book)
	return (" [x] Sent Book about {}".format(book))


if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=True)
