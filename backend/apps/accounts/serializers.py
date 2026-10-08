from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    id = serializers.CharField(read_only=True)

    class Meta:
        model = User
        fields = ["id", "username", "email", "phone", "district", "preferred_language", "date_joined"]
        read_only_fields = ["id", "username", "date_joined"]


class RegisterSerializer(serializers.ModelSerializer):
    id = serializers.CharField(read_only=True)
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ["id", "username", "password", "email", "phone", "district", "preferred_language"]

    def validate_password(self, value):
        validate_password(value)
        return value

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)
