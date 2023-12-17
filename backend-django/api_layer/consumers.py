from asgiref.sync import async_to_sync
from channels.generic.websocket import WebsocketConsumer
from django.contrib.auth.models import User


class StatusConsumer(WebsocketConsumer):
    groups = ['broadcast']

    def connect(self):
        self.accept()

    def disconnect(self, close_code):
        pass

    def receive(self, text_data=None, bytes_data=None):
        User.objects.all()
        async_to_sync(self.channel_layer.group_send)(
            'broadcast', {"type": "chat.message", "message": text_data}
        )

    def chat_message(self, event):
        message = event['message']
        self.send(text_data=message)
