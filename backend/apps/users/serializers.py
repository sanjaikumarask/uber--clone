from rest_framework import serializers
from django.contrib.auth import authenticate, get_user_model

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    role = serializers.ChoiceField(choices=['rider', 'driver'], required=False, default='rider')

    class Meta:
        model = User
        fields = ["id", "phone", "password", "first_name", "last_name", "role"]
        read_only_fields = ["id"]

    def create(self, validated_data):
        password = validated_data.pop("password")
        role = validated_data.pop("role", "rider")  # Get role from data, default to rider
        # Set username to phone to satisfy AbstractUser's unique username constraint
        validated_data["username"] = validated_data.get("phone")
        user = User(**validated_data)
        user.role = role  # Use the role from request
        user.set_password(password)
        user.save()
        return user


class RiderLoginSerializer(serializers.Serializer):
    phone = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        try:
            user = User.objects.get(phone=attrs["phone"])
        except User.DoesNotExist:
            raise serializers.ValidationError("Invalid credentials")

        if not user.check_password(attrs["password"]):
            raise serializers.ValidationError("Invalid credentials")

        if not user.is_rider:
            raise serializers.ValidationError("Not a rider account")

        attrs["user"] = user
        return attrs


class DriverLoginSerializer(serializers.Serializer):
    phone = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        try:
            user = User.objects.get(phone=attrs["phone"])
        except User.DoesNotExist:
            raise serializers.ValidationError("Invalid credentials")

        if not user.check_password(attrs["password"]):
            raise serializers.ValidationError("Invalid credentials")

        if not user.is_driver:
            raise serializers.ValidationError("Not a driver account")

        attrs["user"] = user
        return attrs


class AdminLoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        user = authenticate(
            username=attrs["username"],
            password=attrs["password"],
        )

        if not user:
            raise serializers.ValidationError("Invalid credentials")

        if not user.is_admin:
            raise serializers.ValidationError("Admin access only")

        attrs["user"] = user
        return attrs


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "phone", "role", "first_name", "last_name"]
