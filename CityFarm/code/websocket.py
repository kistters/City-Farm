""" https://github.com/hiroakis/tornado-websocket-example 
melhor exemplo """
from tornado import websocket, web, ioloop
from tasks import plant, eat, verify_tomato_proof
import json, redis, logging, secrets


r = redis.StrictRedis(host='redis', port=6379, db=0)
#logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.DEBUG)

storage = ['corn', 'wheat', 'celery', 'carrot', 'lettuce', 'tomato']
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

    history = [json.loads(item) for item in r.lrange("pow:history", 0, 49)]
    data = {'groceries': groceries, 'pow_history': history}
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
        self.pending_proof = None
        self.write_message(json.dumps({"groceries": storage}))

    def on_message(self, message):
        try:
            message = json.loads(message)
            if not isinstance(message, dict):
                raise ValueError("invalid payload")
        except (TypeError, ValueError):
            self.write_message(json.dumps({"pow_error": "Invalid message"}))
            return

        if message.get("pow_start") == "tomato":
            if self.pending_proof and r.exists("pow:challenge:" + self.pending_proof):
                self.write_message(json.dumps({"pow_error": "A challenge is already running"}))
                return
            challenge_id = secrets.token_hex(16)
            token = secrets.token_hex(16)
            challenge = "cityfarm:v1:{}:tomato:{}".format(challenge_id, token)
            r.setex("pow:challenge:" + challenge_id, 180, challenge)
            self.pending_proof = challenge_id
            self.write_message(json.dumps({"pow_challenge": {
                "id": challenge_id, "challenge": challenge, "difficulty": 3
            }}))
            return

        if "pow_submit" in message:
            data = message["pow_submit"]
            if not isinstance(data, dict):
                self.write_message(json.dumps({"pow_error": "Invalid submission"}))
                return
            challenge_id, nonce = data.get("id"), data.get("nonce")
            if challenge_id != self.pending_proof or not self.pending_proof:
                self.write_message(json.dumps({"pow_error": "Challenge not owned by this connection"}))
                return
            if type(nonce) is not int or not 0 <= nonce <= 10000000:
                self.write_message(json.dumps({"pow_error": "Invalid nonce"}))
                return
            self.pending_proof = None
            verify_tomato_proof.apply_async(
                args=[challenge_id, nonce, self.request.remote_ip],
                queue="planting", serializer="json",
            )
            self.write_message(json.dumps({"pow_status": "submitted"}))
            return

        if message.get("produce") == "tomato":
            self.write_message(json.dumps({"pow_error": "Tomatoes require proof of work"}))
            return

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

        userIp = self.request.remote_ip
        data = {"ipClick": userIp}
        cl_write(data, cl_dashboard)

class FarmRequestHandler(web.RequestHandler):

    def get(self, *args):
        dashboard_update()
        connections_update()
        self.finish()
        
            

app = web.Application([
    (r'/publihser', PublihserHandler),
    (r'/dashboard', DashboardHandler),
    (r'/update', FarmRequestHandler),
], debug=True)

if __name__ == '__main__':
    init()
    app.listen(8888)
    ioloop.IOLoop.instance().start()