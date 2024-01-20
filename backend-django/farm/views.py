from django.contrib.auth.models import User
from django.db.models import Count, Q
from django.utils import timezone
from rest_framework import serializers, generics, permissions
from rest_framework.authentication import TokenAuthentication

from .models import Commodity, Food


class FarmerSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name']


class CommoditySerializer(serializers.ModelSerializer):
    class Meta:
        model = Commodity
        fields = ('id', 'name')


class FoodSerializer(serializers.ModelSerializer):

    class Meta:
        model = Food
        fields = ('id', 'commodity', 'farmer_owner', 'produced_at')
        read_only_fields = ['farmer_owner', 'produced_at']


class CommodityList(generics.ListAPIView):
    queryset = Commodity.objects.all()
    serializer_class = CommoditySerializer
    authentication_classes = (TokenAuthentication,)


class FoodAPIView(generics.CreateAPIView, generics.ListAPIView):
    queryset = Food.objects.all()
    serializer_class = FoodSerializer
    authentication_classes = (TokenAuthentication,)
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def perform_create(self, serializer):
        return serializer.save(farmer_owner=self.request.user, produced_at=timezone.now())

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)


class CommoditySummarySerializer(serializers.ModelSerializer):
    summary = serializers.IntegerField(read_only=True)

    class Meta:
        model = Commodity
        fields = ('id', 'name', 'summary')


class SummaryAPIView(generics.ListAPIView):
    serializer_class = CommoditySummarySerializer
    authentication_classes = (TokenAuthentication,)
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        queryset = Commodity.objects.annotate(
            summary=Count(
                'food_related',
                filter=Q(food_related__farmer_owner=self.request.user)
            )
        )
        return queryset
