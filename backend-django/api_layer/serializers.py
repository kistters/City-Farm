from django.contrib.auth.models import User
from rest_framework import serializers


class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True)
    password2 = serializers.CharField(style={'input_type': 'password'}, write_only=True, required=True)

    class Meta:
        model = User  # get_user_model can be used too.
        fields = ['username', 'password', 'password2']

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})

        if User.objects.filter(username__iexact=attrs['username']).exists():
            raise serializers.ValidationError({"username": "A user with that username already exists."})

        return attrs

    def create(self, validated_data):
        user = User.objects.create(
            username=validated_data['username'],
        )
        user.set_password(validated_data['password'])
        user.save()
        return user
