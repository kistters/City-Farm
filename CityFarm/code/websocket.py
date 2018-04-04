""" https://github.com/hiroakis/tornado-websocket-example 
melhor exemplo """
from tornado import websocket, web, ioloop
from tasks import plant, eat
import random, json, redis


r = redis.StrictRedis(host='redis', port=6379, db=0)

cl_status = []
cl_dashboard = []

def farmer_or_citizen():
    if bool(random.getrandbits(1)):
        eat.apply_async(("wheat",), queue='eating', serializer='json', link=update_dash())
        eat.apply_async(("corn",), queue='eating', serializer='json', link=update_dash())
        return json.dumps({'eat':'citizen'}), 200

    plant.apply_async(["corn"], queue='planting', serializer='json', link=update_dash())
    plant.apply_async(["wheat"], queue='planting', serializer='json', link=update_dash())
    return json.dumps({'plant':'farmer'}), 200

def update_dash():
    data = []
    for what in ['corn', 'wheat']:
        if r.get(what):
            data.append({
                'what':what, 
                'qty':r.get(what).decode('utf8')
                })

    data = json.dumps(data)
    for c in cl_dashboard:
        c.write_message(data)

""" websocket handler """
class StatusHandler(websocket.WebSocketHandler):
    def check_origin(self, origin):
        return True

    def open(self):
        if self not in cl_status:
            cl_status.append(self)

        data = {"message": "{} connections".format(len(cl_status))}
        data = json.dumps(data)
        for c in cl_status:
            c.write_message(data)

    def on_message(self, message):
        data = {"message": message}
        data = json.dumps(data)
        for c in cl_status:
            c.write_message(data)

    def on_close(self):
        if self in cl_status:
            cl_status.remove(self)


class DashboardHandler(websocket.WebSocketHandler):
    def check_origin(self, origin):
        return True

    def open(self):
        if self not in cl_dashboard:
            cl_dashboard.append(self)

    def on_message(self, message):
        data = []
        for what in ['corn', 'wheat']:
            if r.get(what):
                data.append({
                    'what':what, 
                    'qty':r.get(what).decode('utf8')
                    })

        data = json.dumps(data)
        for c in cl_dashboard:
            c.write_message(data)

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