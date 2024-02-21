from channels.generic.websocket import JsonWebsocketConsumer
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.contrib.auth.models import User
from django.db.models import Count


def update_websocket_dashboard():
    channel_layer = get_channel_layer()
    top_farmer = User.objects.annotate(
        score=Count('produced_food')
    ).filter(score__gt=0).order_by(
        '-score'
    ).values('username', 'score')

    message = {
        'type': 'broadcast_message',
        'message': {
            'top_farmer': list(top_farmer),
        }
    }
    async_to_sync(channel_layer.group_send)('broadcast', message)


class StatusConsumer(JsonWebsocketConsumer):
    groups = ['broadcast']

    def connect(self):
        self.accept()

    def receive_json(self, content, **kwargs):
        message = content['message']
        if 'dashboard' in message:
            update_websocket_dashboard()
            # self.send_json({
            #     'reply': 'received your message: {}'.format(content)
            # })

    def broadcast_message(self, content):
        message = content['message']
        self.send_json(content=message)
