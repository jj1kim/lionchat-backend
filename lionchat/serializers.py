from rest_framework import serializers

from .models import User, ChatLog


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'name']


class SignupSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model = User
        fields = ['email', 'name', 'password']

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class ChatLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatLog
        fields = ['id', 'prompt', 'response', 'created_at']


class ChatRequestSerializer(serializers.Serializer):
    prompt = serializers.CharField(max_length=2000)
