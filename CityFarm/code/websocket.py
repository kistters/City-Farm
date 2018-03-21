""" https://github.com/hiroakis/tornado-websocket-example 
melhor exemplo """
from tornado import websocket, web, ioloop
import json, logging

logging.basicConfig(filename='log/websocket.log',level=logging.DEBUG)

cl = []

class IndexHandler(web.RequestHandler):
    def get(self):
        self.render("index.html")

class SocketHandler(websocket.WebSocketHandler):
    def check_origin(self, origin):
        return True

    def open(self):
        if self not in cl:
            cl.append(self)

    def on_close(self):
        if self in cl:
            cl.remove(self)

class ApiHandler(web.RequestHandler):

    @web.asynchronous
    def get(self, *args):
        self.finish()
        message = self.get_argument("message")
        data = {"message": message}
        data = json.dumps(data)
        for c in cl:
            c.write_message(data)

app = web.Application([
    (r'/', IndexHandler),
    (r'/ws', SocketHandler),
    (r'/api', ApiHandler),
])

if __name__ == '__main__':
    app.listen(8888)
    ioloop.IOLoop.instance().start()