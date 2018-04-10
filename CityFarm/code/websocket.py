""" https://github.com/hiroakis/tornado-websocket-example 
melhor exemplo """
from tornado import websocket, web, ioloop
from tasks import plant, eat
import json, redis, logging


r = redis.StrictRedis(host='redis', port=6379, db=0)
#logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.DEBUG)

storage = ['corn', 'wheat']
cl_dashboard = []


def farmer(what):
    res = plant.apply_async([what], queue='planting', serializer='json')

def citizen(what):
    res = eat.apply_async((what,), queue='eating', serializer='json')

def init():
    for what in storage:
        r.incr(what)
        r.decr(what)

def cl_write(data, cl_list):
    data = json.dumps(data)
    for c in cl_list:
        c.write_message(data)

""" application info """
def dashboard_update():
    groceries = []
    for what in storage:
        if r.get(what):
            groceries.append({
                'what':what, 
                'qty':r.get(what).decode('utf8')
                })

    data = {'groceries':groceries}
    cl_write(data, cl_dashboard)


""" info system """
def connections_update():
    userIpList = []
    for c in cl_dashboard:
        userIpList.append(c.request.remote_ip)

    data = {"cl_count": len(cl_dashboard), "userIpList": list(set(userIpList))}

    cl_write(data, cl_dashboard)

""" websocket handler """
class DashboardHandler(websocket.WebSocketHandler):

    def check_origin(self, origin):
        return True

    def open(self):
        if self not in cl_dashboard:
            cl_dashboard.append(self)

        dashboard_update()
        connections_update()
        
    def on_message(self, message):
        data = {"global_msg": message}
        data = json.dumps(data)
        for c in cl_dashboard:
            c.write_message(data)

    def on_close(self):
        if self in cl_dashboard:
            cl_dashboard.remove(self)

        dashboard_update()
        connections_update()

class PublihserHandler(websocket.WebSocketHandler):

    def check_origin(self, origin):
        return True

    def open(self):
        self.write_message(json.dumps({"groceries": storage}))

    def on_message(self, message):

        message = json.loads(message)

        if message.get('produce'):
            farmer(message.get('produce'))
            produce_key = "produce:{}".format(self.request.remote_ip)
            r.incr(produce_key)
            work = r.get(produce_key).decode('utf8')
            self.write_message(json.dumps({"work": work}))

        if message.get('consume'):
            citizen(message.get('consume'))
            consume_key = "consume:{}".format(self.request.remote_ip)
            r.incr(consume_key)
            work = r.get(consume_key).decode('utf8')
            self.write_message(json.dumps({"work": work}))


class FarmRequestHandler(web.RequestHandler):

    @web.asynchronous
    def get(self, *args):
        self.finish()

        dashboard_update()
        connections_update()
        
            

app = web.Application([
    (r'/publihser', PublihserHandler),
    (r'/dashboard', DashboardHandler),
    (r'/update', FarmRequestHandler),
], debug=True)

if __name__ == '__main__':
    init()
    app.listen(8888)
    ioloop.IOLoop.instance().start()