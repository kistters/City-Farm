from django.contrib.auth.models import User
from rest_framework import serializers

from farm.models import Commodity, Food
from city.models import Job, Money


class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True)
    password2 = serializers.CharField(style={'input_type': 'password'}, write_only=True, required=True)

    class Meta:
        model = User  # get_user_model can be used too.
        fields = ['username', 'password', 'password2']

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        return attrs

    def create(self, validated_data):
        user = User.objects.create(
            username=validated_data['username'],
        )
        user.set_password(validated_data['password'])
        user.save()
        return user


class CommoditySerializer(serializers.ModelSerializer):
    class Meta:
        model = Commodity
        fields = ('id', 'name')


class FoodSerializer(serializers.ModelSerializer):
    class Meta:
        model = Food
        fields = ('id', 'commodity', 'farmer_owner', 'produced_at')
        read_only_fields = ['farmer_owner', 'produced_at']


class CommoditySummarySerializer(serializers.ModelSerializer):
    summary = serializers.IntegerField(read_only=True)

    class Meta:
        model = Commodity
        fields = ('id', 'name', 'summary')


class JobSerializer(serializers.ModelSerializer):
    class Meta:
        model = Job
        fields = ('id', 'name')


class MoneySerializer(serializers.ModelSerializer):
    class Meta:
        model = Money
        fields = ('id', 'job', 'citizen_owner', 'produced_at')
        read_only_fields = ['citizen_owner', 'produced_at']


class JobSummarySerializer(serializers.ModelSerializer):
    summary = serializers.IntegerField(read_only=True)

    class Meta:
        model = Job
        fields = ('id', 'name', 'summary')
