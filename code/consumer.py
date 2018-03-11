#!/usr/bin/env python
import pika

connection = pika.BlockingConnection(pika.ConnectionParameters(host='rabbitmq'))
channel = connection.channel()

channel.queue_declare(queue='hello')

def callback(ch, method, properties, body):

	f= open("../data/list.txt","a")
	f.write("[x] Received {}\n".format(repr(body)))
	f.write("{}".format(body.json()))
	f.close()

channel.basic_consume(callback,
                      queue='hello',
                      no_ack=True)

channel.start_consuming()