from django.contrib.auth import authenticate
from django.utils import timezone

from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import CreateAPIView
from rest_framework import generics, permissions
from rest_framework.authentication import TokenAuthentication

from api_layer.serializers import (
    UserSerializer,
    JobSerializer, MoneySerializer, JobSummarySerializer,
    CommoditySerializer, FoodSerializer, CommoditySummarySerializer,
)

from city.models import Job, Money
from farm.models import Commodity, Food


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


class CommodityListView(generics.ListAPIView):
    queryset = Commodity.objects.all()
    serializer_class = CommoditySerializer
    authentication_classes = (TokenAuthentication,)


class ProduceFoodAPIView(generics.CreateAPIView):
    queryset = Food.objects.all()
    serializer_class = FoodSerializer
    authentication_classes = (TokenAuthentication,)
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def perform_create(self, serializer):
        return serializer.save(farmer_owner=self.request.user, produced_at=timezone.now())


class CommoditySummaryAPIView(generics.ListAPIView):
    serializer_class = CommoditySummarySerializer
    authentication_classes = (TokenAuthentication,)
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        from django.db.models import Count
        from django.db.models import Q
        queryset = Commodity.objects.annotate(
            summary=Count(
                'food_related',
                filter=Q(food_related__farmer_owner=self.request.user)
            )
        )
        return queryset


class JobListView(generics.ListAPIView):
    queryset = Job.objects.all()
    serializer_class = JobSerializer
    authentication_classes = (TokenAuthentication,)


class DoTheWorkAPIView(generics.CreateAPIView):
    queryset = Money.objects.all()
    serializer_class = MoneySerializer
    authentication_classes = (TokenAuthentication,)
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def perform_create(self, serializer):
        return serializer.save(citizen_owner=self.request.user, produced_at=timezone.now())


class JobSummaryAPIView(generics.ListAPIView):
    serializer_class = JobSummarySerializer
    authentication_classes = (TokenAuthentication,)
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        from django.db.models import Count
        from django.db.models import Q
        queryset = Job.objects.annotate(
            summary=Count(
                'job_related',
                filter=Q(job_related__citizen_owner=self.request.user)
            )
        )
        return queryset
