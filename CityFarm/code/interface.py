""" for producer and consumer """

def plant(what, qty):
	pass


def eat(what, qty):
	pass


import logging
logging.basicConfig(filename='log/example.log',level=logging.DEBUG)
logging.debug('This message should go to the log file')
logging.info('So should this')
logging.warning('And this, too')