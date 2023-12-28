from channels.generic.websocket import JsonWebsocketConsumer
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.contrib.auth.models import User
from django.db.models import Count


def update_websocket_dashboard():
    channel_layer = get_channel_layer()
    top_farmer = User.objects.annotate(
        score=Count('produced_ingredients')
    ).filter(score__gt=0).order_by(
        '-score'
    ).values('username', 'score')

    top_citizen = User.objects.annotate(
        score=Count('bought_ingredients')
    ).filter(score__gt=0).order_by(
        '-score'
    ).values('username', 'score')

    message = {
        'type': 'broadcast_message',
        'message': {
            'top_farmer': list(top_farmer),
            'top_citizen': list(top_citizen),
        }
    }
    async_to_sync(channel_layer.group_send)('broadcast', message)


def message_websocket_dashboard(ingredient):
    channel_layer = get_channel_layer()
    message = {
        'type': 'broadcast_message',
        'message': {
            'missing_ingredient': ingredient,
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

    # def receive(self, text_data=None, bytes_data=None):
    #     User.objects.all()
    #     async_to_sync(self.channel_layer.group_send)(
    #         'broadcast', {"type": "chat.message", "message": text_data}
    #     )

    def broadcast_message(self, content):
        message = content['message']
        self.send_json(content=message)
