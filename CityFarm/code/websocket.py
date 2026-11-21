""" https://github.com/hiroakis/tornado-websocket-example 
melhor exemplo """
from tornado import websocket, web, ioloop
from tasks import verify_product_proof
import json, redis, logging, secrets
from products import PRODUCT_DIFFICULTIES, public_catalog
from dishes import DISHES, public_dishes
from dish_orders import enqueue_dish, fulfill_pending_dishes
from eat_orders import enqueue_eat, recover_pending_orders
from players import normalize_player


r = redis.StrictRedis(host='redis', port=6379, db=0)
#logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.DEBUG)

storage = list(PRODUCT_DIFFICULTIES)
cl_dashboard = []


def citizen(what):
    """Persist a single-ingredient demand; no Celery task or retry."""
    if what not in storage:
        raise ValueError("Unknown product")
    order = enqueue_eat(r, what, secrets.token_hex(16))
    dashboard_update()
    return order


def init():
    # Convert old pending markers to FIFO once, and settle outstanding
    # orders already covered by stock. Safe on repeated restarts.
    recover_pending_orders(r)
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
    pending_orders = [
        {"what": what, "qty": max(0, int(r.get("eat:waiting:" + what) or 0))}
        for what in storage
    ]
    data = {
        'groceries': groceries, 'pow_history': history,
        'pending_orders': pending_orders,
        'product_catalog': public_catalog(),
        'pending_dishes': [
            {"id": dish_id, "qty": int(r.get("dish:waiting:" + dish_id) or 0)}
            for dish_id in DISHES
        ],
    }
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
        self.player = None
        self.write_message(json.dumps({
            "groceries": storage,
            "product_catalog": public_catalog(),
            "dishes": public_dishes(),
        }))

    def on_message(self, message):
        try:
            message = json.loads(message)
            if not isinstance(message, dict):
                raise ValueError("invalid payload")
        except (TypeError, ValueError):
            self.write_message(json.dumps({"pow_error": "Invalid message"}))
            return

        if "player_register" in message:
            profile = message["player_register"]
            if not isinstance(profile, dict):
                self.write_message(json.dumps({"player_error": "Invalid profile"}))
                return
            try:
                player = normalize_player(profile.get("id"), profile.get("name"))
            except ValueError as error:
                self.write_message(json.dumps({"player_error": str(error)}))
                return
            self.player = player
            # Names are cosmetic: no credentials, verification or ownership claims.
            self.write_message(json.dumps({"player_registered": player}))
            return

        if "pow_start" in message:
            if self.player is None:
                self.write_message(json.dumps({"pow_error": "Choose a Farmer name first"}))
                return
            product = message["pow_start"]
            if product not in PRODUCT_DIFFICULTIES:
                self.write_message(json.dumps({"pow_error": "Unknown product"}))
                return
            if self.pending_proof and r.exists("pow:challenge:" + self.pending_proof):
                self.write_message(json.dumps({"pow_error": "A challenge is already running"}))
                return
            challenge_id = secrets.token_hex(16)
            token = secrets.token_hex(16)
            challenge = "cityfarm:v1:{}:{}:{}".format(challenge_id, product, token)
            r.setex("pow:challenge:" + challenge_id, 180, json.dumps({
                "challenge": challenge, "product": product,
                "difficulty": PRODUCT_DIFFICULTIES[product],
                "farmer": self.player,
            }))
            self.pending_proof = challenge_id
            self.write_message(json.dumps({"pow_challenge": {
                "id": challenge_id, "challenge": challenge,
                "product": product, "difficulty": PRODUCT_DIFFICULTIES[product]
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
            verify_product_proof.apply_async(
                args=[challenge_id, nonce, self.player],
                queue="planting", serializer="json",
            )
            self.write_message(json.dumps({"pow_status": "submitted"}))
            return

        if "order_dish" in message:
            dish_id = message["order_dish"]
            if not isinstance(dish_id, str) or dish_id not in DISHES:
                self.write_message(json.dumps({"dish_error": "Unknown dish"}))
                return
            if r.llen("dish:pending:ids") >= 200:
                self.write_message(json.dumps({"dish_error": "Dish queue is full"}))
                return
            order_id = secrets.token_hex(16)
            enqueue_dish(r, order_id, dish_id)
            fulfill_pending_dishes(r)
            status = "waiting" if r.exists("dish:pending:" + order_id) else "prepared"
            dashboard_update()
            self.write_message(json.dumps({
                "dish_ordered": {"dish": dish_id, "id": order_id,
                                 "status": status}
            }))
            return

        if "produce" in message:
            self.write_message(json.dumps({"pow_error": "Use proof of work for production"}))
            return

        if message.get('consume'):
            if message['consume'] not in storage:
                self.write_message(json.dumps({"eat_error": "Unknown product"}))
                return
            try:
                order = citizen(message.get('consume'))
            except ValueError as error:
                self.write_message(json.dumps({"eat_error": str(error)}))
                return
            self.write_message(json.dumps({
                "eat_ordered": {"product": message["consume"],
                                "status": "prepared" if order["fulfilled"] else "waiting"}
            }))
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