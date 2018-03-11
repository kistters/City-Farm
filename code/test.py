import pika

connection = pika.BlockingConnection(pika.ConnectionParameters(host='rabbitmq'))

channel = connection.channel()
channel.queue_declare(queue='hello')

languages = ['Python', 'Java', 'Ruby', 'Go', 'C', 'Haskell', 'Shell', 'Lua', 'Php', 'javaScript', 'Cobol']

for lang in languages :
	""" create all publish to test """

	channel.basic_publish(exchange='',
                      routing_key='hello',
                      body=lang)
	print(" [x] Sent Book about {}".format(lang))


"""print all publish test"""
def callback(ch, method, properties, body):
	print(body)



channel.basic_consume(callback, queue='hello', no_ack=True)

print(' [*] Waiting for messages. To exit press CTRL+C')
try:
    channel.start_consuming()
except KeyboardInterrupt:
    channel.stop_consuming()
connection.close()
