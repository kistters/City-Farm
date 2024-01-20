from django.contrib.auth import authenticate
from django.utils import timezone
from rest_framework import status
from rest_framework.authentication import TokenAuthentication
from rest_framework.authtoken.models import Token
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import CreateAPIView

from .consumers import update_websocket_dashboard, message_websocket_dashboard
from .serializers import UserSerializer, IngredientSerializer


class RegisterView(CreateAPIView):
    serializer_class = UserSerializer


class LoginView(APIView):
    def post(self, request):
        username = request.data.get("username")
        password = request.data.get("password")
        user = authenticate(username=username, password=password)
        if user:
            token, _ = Token.objects.get_or_create(user=user)
            return Response({"token": token.key}, status=status.HTTP_200_OK)
        else:
            return Response({"error": "Wrong Credentials"}, status=status.HTTP_400_BAD_REQUEST)


class LogoutView(APIView):
    authentication_classes = [TokenAuthentication]

    def post(self, request):
        if request.user.is_authenticated:
            request.user.auth_token.delete()
        return Response(status=204)
