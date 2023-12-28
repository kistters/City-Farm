from django.contrib.auth import authenticate
from django.utils import timezone
from rest_framework import status
from rest_framework.authentication import TokenAuthentication
from rest_framework.authtoken.models import Token
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import CreateAPIView

from ingredients.models import Ingredient
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


class ProduceIngredientView(APIView):
    authentication_classes = (TokenAuthentication,)

    def post(self, request):
        data = request.data
        data['producer'] = request.user.id
        data['produced_at'] = timezone.now()

        serializer = IngredientSerializer(data=data)
        if serializer.is_valid():
            ingredient = serializer.save()
            update_websocket_dashboard()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class BuyIngredientView(APIView):
    authentication_classes = (TokenAuthentication,)

    def post(self, request):
        data = request.data

        chosen_ingredient = Ingredient.objects.filter(
            buyer__isnull=True,
            bought_at__isnull=True,
            name__iexact=data.get('name'),
        ).exclude(
            producer=request.user
        ).order_by('?').first()

        if not chosen_ingredient:
            message_websocket_dashboard(data.get('name'))

        data['id'] = chosen_ingredient.id
        data['buyer'] = request.user.id
        data['bought_at'] = timezone.now()

        serializer = IngredientSerializer(instance=chosen_ingredient, data=data, partial=True)
        if serializer.is_valid():
            ingredient = serializer.save()
            update_websocket_dashboard()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
