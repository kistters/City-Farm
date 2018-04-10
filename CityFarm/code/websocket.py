""" https://github.com/hiroakis/tornado-websocket-example 
melhor exemplo """
from tornado import websocket, web, ioloop
from tasks import plant, eat
import random, json, redis, logging


r = redis.StrictRedis(host='redis', port=6379, db=0)
#logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.DEBUG)

cl_status = []
cl_dashboard = []


def farmer(what):
    plant.apply_async([what], queue='planting', serializer='json', link=update_dash())
    return

def citizen(what):
    eat.apply_async((what,), queue='eating', serializer='json', callback=logTest())
    return

def logTest():
     logging.warning('tes')

def update_dash():
    data = []
    for what in ['corn', 'wheat']:
        if r.get(what):
            data.append({
                'what':what, 
                'qty':r.get(what).decode('utf8')
                })

    data = json.dumps({'groceries':data})
    for c in cl_status:
        c.write_message(data)

def update_status():
    listUser = []
    for c in cl_status:
        listUser.append(c.request.remote_ip)

    data = {"message": "{} connections".format(len(cl_status)), "listUser": list(set(listUser))}
    data = json.dumps(data)
    for c in cl_status:
        c.write_message(data)

""" websocket handler """
class StatusHandler(websocket.WebSocketHandler):

    def check_origin(self, origin):
        return True

    def open(self):
        if self not in cl_status:
            cl_status.append(self)

        update_status()
        update_dash()
        
    def on_message(self, message):
        data = {"message": message}
        data = json.dumps(data)
        for c in cl_status:
            c.write_message(data)

    def on_close(self):
        if self in cl_status:
            cl_status.remove(self)

        update_status()


class DashboardHandler(websocket.WebSocketHandler):
    def check_origin(self, origin):
        return True

    def open(self):
        if self not in cl_dashboard:
            cl_dashboard.append(self)

    def on_message(self, message):

        message = json.loads(message)

        if message.get('produce'):
            farmer(message.get('produce'))
            r.incr(self.request.remote_ip)

        if message.get('consume'):
            citizen(message.get('consume'))
            r.incr(self.request.remote_ip)

        if r.get(self.request.remote_ip):
            work = r.get(self.request.remote_ip).decode('utf8')
            self.write_message(json.dumps({"work": work}))

        update_dash()

    def on_close(self):
        if self in cl_dashboard:
            cl_dashboard.remove(self)


class FarmRequestHandler(web.RequestHandler):

    @web.asynchronous
    def get(self, *args):
        self.finish()
        farmer_or_citizen()
        
            

app = web.Application([
    (r'/status', StatusHandler),
    (r'/dashboard', DashboardHandler),
    (r'/update', FarmRequestHandler),
], debug=True)

if __name__ == '__main__':
    app.listen(8888)
    ioloop.IOLoop.instance().start()