import uuid

from channels.generic.websocket import WebsocketConsumer


class StatusConsumer(WebsocketConsumer):
    def connect(self):
        self.accept()

    def disconnect(self, close_code):
        pass

    def receive(self, text_data=None, bytes_data=None):
        self.send(text_data=f"{text_data} - {self.scope['client'][0]} - {uuid.uuid4().hex}")


class SecretConsumer(WebsocketConsumer):
    def connect(self):
        self.accept()

    def disconnect(self, close_code):
        pass

    def receive(self, text_data=None, bytes_data=None):
        self.send(text_data=f"Secret {text_data}")
