""" https://github.com/hiroakis/tornado-websocket-example 
melhor exemplo """
from tornado import websocket, web, ioloop
import json, redis

r = redis.StrictRedis(host='redis', port=6379, db=0)

cl_msg = []
cl_status = []


class MessageHandler(websocket.WebSocketHandler):
    def check_origin(self, origin):
        return True

    def open(self):
        if self not in cl_msg:
            cl_msg.append(self)

    def on_message(self, message):
        data = {"message": message}
        data = json.dumps(data)
        for c in cl_msg:
            c.write_message(data)

    def on_close(self):
        if self in cl_msg:
            cl_msg.remove(self)


class StatusHandler(websocket.WebSocketHandler):
    def check_origin(self, origin):
        return True

    def open(self):
        if self not in cl_status:
            cl_status.append(self)

    def on_close(self):
        if self in cl_status:
            cl_status.remove(self)


class FarmRequestHandler(web.RequestHandler):

    @web.asynchronous
    def get(self, *args):
        self.finish()

        data = {'corn':0 , 'wheat': 0}
        if r.get('corn'):
           data['corn'] = r.get('corn').decode('utf8')

        if r.get('wheat'):
            data['wheat'] = r.get('wheat').decode('utf8')

        data = json.dumps(data)
        for c in cl_status:
            c.write_message(data)
            

app = web.Application([
    (r'/message', MessageHandler),
    (r'/status', StatusHandler),
    (r'/update', FarmRequestHandler),
], debug=True)

if __name__ == '__main__':
    app.listen(8888)
    ioloop.IOLoop.instance().start()