"""Servidor WebSocket do City-Farm: transporte, não regras do jogo."""
import json
import logging
from datetime import datetime, timezone

import redis
import psycopg
from tornado import ioloop, web, websocket

from economy import (cancel_farming_challenge, complete_challenge,
                     get_food_market_status, get_player_resource_status,
                     list_character_summaries, prepare_soil_with_coins,
                     purchase_food, recover_energy_with_rest,
                     recover_soil_health, register_player_character,
                     start_challenge)
from models import PlayerProfile
from economy_repository import EconomyRepository

red = redis.StrictRedis(host="redis", port=6379, db=0)
dashboard_clients = set()
players = set()


def send(handler, data):
    handler.write_message(json.dumps(data))


def dashboard_snapshot():
    history = [json.loads(item) for item in red.lrange("game:history", 0, 49)]
    return {"market": get_food_market_status(red), "history": history,
            "characters": list_character_summaries(red)}


def dashboard_update():
    payload = dashboard_snapshot()
    for client in list(dashboard_clients):
        try:
            send(client, payload)
        except websocket.WebSocketClosedError:
            dashboard_clients.discard(client)


def record_event(kind, actor, details):
    event = {
        "kind": kind, "actor": actor.nickname, "details": details,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    pipe = red.pipeline()
    pipe.lpush("game:history", json.dumps(event))
    pipe.ltrim("game:history", 0, 49)
    pipe.execute()


def broadcast():
    current_market = get_food_market_status(red)
    for client in list(players):
        try:
            payload = {"market": current_market}
            if client.player:
                payload["player_state"] = get_player_resource_status(
                    red, client.player.player_id)
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


class PlayerHandler(websocket.WebSocketHandler):
    def check_origin(self, origin):
        return True

    def open(self):
        self.player = None
        players.add(self)
        send(self, {"market": get_food_market_status(red)})

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
                player = PlayerProfile.from_registration(
                    profile.get("id"), profile.get("name"))
                register_player_character(
                    red, player.player_id, player.nickname, profile.get("role"))
                self.player = player
                send(self, {"player_registered": player.as_payload(),
                            "player_state": get_player_resource_status(
                                red, player.player_id)})
                dashboard_update()
                return
            if not self.player:
                raise ValueError("Choose a nickname and join first")
            owner = self.player.player_id
            if "farm_start" in message:
                request = message["farm_start"]
                if not isinstance(request, dict):
                    raise ValueError("Invalid farm request")
                challenge = start_challenge(red, owner, "farmer", request.get("level"))
                send(self, {"challenge": challenge})
            elif "farm_cancel" in message:
                request = message["farm_cancel"]
                if not isinstance(request, dict):
                    raise ValueError("Invalid cancellation")
                result = cancel_farming_challenge(red, owner, request.get("id"))
                send(self, {"challenge_cancelled": result})
            elif "work_start" in message:
                request = message["work_start"]
                if not isinstance(request, dict):
                    raise ValueError("Invalid work request")
                challenge = start_challenge(red, owner, "citizen", request.get("level"))
                send(self, {"challenge": challenge})
            elif "challenge_submit" in message:
                request = message["challenge_submit"]
                if not isinstance(request, dict):
                    raise ValueError("Invalid answer")
                outcome = complete_challenge(red, owner, request.get("id"), request.get("answer"))
                send(self, {"challenge_result": outcome})
                record_event(outcome["kind"], self.player, outcome["reward"])
                broadcast()
            elif message.get("care_for_soil") is True:
                result = recover_soil_health(red, owner)
                send(self, {"care_result": result})
                broadcast()
            elif message.get("prepare_soil") is True:
                result = prepare_soil_with_coins(red, owner)
                send(self, {"care_result": result})
                record_event("soil_prepared", self.player, result)
                broadcast()
            elif message.get("rest") is True:
                result = recover_energy_with_rest(red, owner)
                send(self, {"rest_result": result})
                broadcast()
            elif message.get("buy_food") is True:
                result = purchase_food(red, owner)
                send(self, {"purchase_result": result})
                record_event("purchase", self.player,
                             {"product": result["product"], "price": result["price"]})
                broadcast()
            else:
                raise ValueError("Unsupported action")
        except (ValueError, TypeError, KeyError, IndexError) as error:
            send(self, {"game_error": str(error)})
        except (redis.RedisError, psycopg.Error):
            logging.exception("Storage command failed")
            send(self, {"game_error": "Storage temporarily unavailable"})


app = web.Application([
    (r"/player", PlayerHandler),
    (r"/dashboard", DashboardHandler),
])

if __name__ == "__main__":
    EconomyRepository().initialize_schema()
    app.listen(8888)
    ioloop.IOLoop.current().start()
