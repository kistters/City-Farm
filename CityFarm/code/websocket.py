"""Servidor WebSocket do City-Farm: transporte, não regras do jogo."""
import json
import logging
from datetime import datetime, timezone

import redis
from tornado import ioloop, web, websocket

from economy import buy, market, start, state, submit, upgrade_plot
from players import normalize_player
from products import public_catalog

red = redis.StrictRedis(host="redis", port=6379, db=0)
dashboard_clients = set()
players = set()


def send(handler, data):
    handler.write_message(json.dumps(data))


def dashboard_snapshot():
    history = [json.loads(item) for item in red.lrange("game:history", 0, 49)]
    return {"market": market(red), "history": history,
            "product_catalog": public_catalog()}


def dashboard_update():
    payload = dashboard_snapshot()
    for client in list(dashboard_clients):
        try:
            send(client, payload)
        except websocket.WebSocketClosedError:
            dashboard_clients.discard(client)


def record_event(kind, actor, details):
    event = {
        "kind": kind, "actor": actor["name"], "details": details,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    pipe = red.pipeline()
    pipe.lpush("game:history", json.dumps(event))
    pipe.ltrim("game:history", 0, 49)
    pipe.execute()


def broadcast():
    current_market = market(red)
    for client in list(players):
        try:
            payload = {"market": current_market}
            if client.player:
                payload["player_state"] = state(red, client.player["id"])
            send(client, payload)
        except websocket.WebSocketClosedError:
            players.discard(client)
    dashboard_update()


class DashboardHandler(websocket.WebSocketHandler):
    def check_origin(self, origin):
        return True  # Demonstração para a rede local; não é autenticação.

    def open(self):
        dashboard_clients.add(self)
        send(self, dashboard_snapshot())

    def on_close(self):
        dashboard_clients.discard(self)


class PublihserHandler(websocket.WebSocketHandler):
    def check_origin(self, origin):
        return True

    def open(self):
        self.player = None
        players.add(self)
        send(self, {"product_catalog": public_catalog(), "market": market(red)})

    def on_close(self):
        players.discard(self)

    def on_message(self, raw):
        try:
            message = json.loads(raw)
            if not isinstance(message, dict):
                raise ValueError("Invalid message")
            if "player_register" in message:
                profile = message["player_register"]
                if not isinstance(profile, dict):
                    raise ValueError("Invalid profile")
                self.player = normalize_player(profile.get("id"), profile.get("name"))
                send(self, {"player_registered": self.player,
                            "player_state": state(red, self.player["id"])})
                return
            if not self.player:
                raise ValueError("Choose a nickname and join first")
            owner = self.player["id"]
            if "farm_start" in message:
                request = message["farm_start"]
                if not isinstance(request, dict):
                    raise ValueError("Invalid farm request")
                challenge = start(red, owner, "farmer", request.get("level"),
                                  product=request.get("product"), plot=request.get("plot"))
                send(self, {"challenge": challenge})
            elif "work_start" in message:
                request = message["work_start"]
                if not isinstance(request, dict):
                    raise ValueError("Invalid work request")
                challenge = start(red, owner, "citizen", request.get("level"))
                send(self, {"challenge": challenge})
            elif "challenge_submit" in message:
                request = message["challenge_submit"]
                if not isinstance(request, dict):
                    raise ValueError("Invalid answer")
                outcome = submit(red, owner, request.get("id"), request.get("answer"))
                send(self, {"challenge_result": outcome})
                record_event(outcome["kind"], self.player, outcome["reward"])
                broadcast()
            elif "upgrade_plot" in message:
                result = upgrade_plot(red, owner)
                send(self, {"upgrade_result": result})
                record_event("upgrade", self.player, result)
                broadcast()
            elif "buy_food" in message:
                result = buy(red, owner, message["buy_food"])
                send(self, {"purchase_result": result})
                record_event("purchase", self.player,
                             {"product": result["product"], "price": result["price"]})
                broadcast()
            else:
                raise ValueError("Unsupported action")
        except (ValueError, TypeError, KeyError, IndexError) as error:
            send(self, {"game_error": str(error)})
        except redis.RedisError:
            logging.exception("Redis command failed")
            send(self, {"game_error": "Storage temporarily unavailable"})


app = web.Application([
    (r"/publihser", PublihserHandler),
    (r"/dashboard", DashboardHandler),
])

if __name__ == "__main__":
    app.listen(8888)
    ioloop.IOLoop.current().start()
