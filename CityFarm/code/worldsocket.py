"""Presence WebSocket for the overworld; separate from economic transactions."""
import json
import logging
import secrets

import psycopg
from tornado import websocket

from economy_repository import EconomyRepository
from models import PlayerProfile
from world import WorldState


WORLD = WorldState()
CLIENTS = set()


def publish(payload, exclude=None):
    message = json.dumps(payload)
    for client in list(CLIENTS):
        if client is exclude:
            continue
        try:
            client.write_message(message)
        except websocket.WebSocketClosedError:
            CLIENTS.discard(client)


class WorldHandler(websocket.WebSocketHandler):
    def check_origin(self, origin):
        return True  # Local-network prototype; not suitable for public internet.

    def open(self):
        self.session = secrets.token_hex(12)

    def on_close(self):
        CLIENTS.discard(self)
        if WORLD.leave(self.session):
            publish({"world_left": self.session})

    def on_message(self, raw):
        try:
            message = json.loads(raw)
            if not isinstance(message, dict):
                raise ValueError("Invalid world message")
            if "world_join" in message:
                if self in CLIENTS:
                    raise ValueError("Already in the world")
                registration = message["world_join"]
                if not isinstance(registration, dict):
                    raise ValueError("Invalid player")
                profile = PlayerProfile.from_registration(
                    registration.get("id"), registration.get("name"))
                role = registration.get("role")
                if role not in ("farmer", "citizen"):
                    raise ValueError("Choose Farmer or Citizen")
                EconomyRepository().save_player_character(
                    profile.player_id, profile.nickname, role)
                player = WORLD.join(self.session, profile, role)
                CLIENTS.add(self)
                self.write_message(json.dumps({
                    "world_snapshot": WORLD.snapshot(), "you": self.session
                }))
                publish({"world_joined": player}, exclude=self)
            elif "world_move" in message:
                delta = message["world_move"]
                if not isinstance(delta, dict):
                    raise ValueError("Invalid movement")
                moved = WORLD.move(self.session, delta.get("dx"), delta.get("dy"))
                if moved:
                    publish({"world_moved": moved})
            else:
                raise ValueError("Unsupported world action")
        except (ValueError, TypeError, KeyError) as error:
            self.write_message(json.dumps({"world_error": str(error)}))
        except psycopg.Error:
            logging.exception("World player registration failed")
            self.write_message(json.dumps({
                "world_error": "Storage temporarily unavailable"
            }))
