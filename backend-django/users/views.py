from django.core.serializers import serialize
from django.http import JsonResponse

from .models import User


def user_list(request):
    users = User.objects.all().values("username", "is_farmer", "is_citizen")
    user_list = list(users)
    return JsonResponse(user_list, safe=False)


def user_detail(request, username):
    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist as e:
        return User.objects.none()

    return user
