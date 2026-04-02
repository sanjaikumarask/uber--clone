import sys
import random
from django.contrib.auth import authenticate, get_user_model
from django.db.models import Q
from rest_framework import serializers

User = get_user_model()


INVALID_CREDENTIALS_MSG = "Invalid credentials"


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    role = serializers.ChoiceField(
        choices=["rider", "driver"], required=False, default="rider"
    )

    class Meta:
        model = User
        fields = ["id", "phone", "email", "password", "first_name", "last_name", "role"]
        read_only_fields = ["id"]
        extra_kwargs = {
            "phone": {"required": True},
            "password": {"write_only": True},
        }

    def create(self, validated_data):
        password = validated_data.pop("password")
        role = validated_data.pop(
            "role", "rider"
        )  # Get role from data, default to rider
        user = User(**validated_data)
        user.role = role  # Use the role from request
        # Ensure unique username
        user.username = validated_data.get("phone") or validated_data.get("email") or str(random.randint(1000000, 9999999))
        user.set_password(password)
        user.save()
        return user


class RiderLoginSerializer(serializers.Serializer):
    phone = serializers.CharField()  # This field can accept phone or email
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        value = attrs["phone"]
        try:
            user = User.objects.filter(Q(phone=value) | Q(email=value)).first()
            if not user:
                sys.stderr.write(f"\n[LOGIN_ERROR] User not found for identifier: {value}\n")
                sys.stderr.flush()
                raise serializers.ValidationError(INVALID_CREDENTIALS_MSG)
        except Exception as e:
            if not isinstance(e, serializers.ValidationError):
                sys.stderr.write(f"\n[LOGIN_ERROR] Exception during lookup: {str(e)}\n")
                sys.stderr.flush()
            raise serializers.ValidationError(INVALID_CREDENTIALS_MSG)

        if not user.check_password(attrs["password"]):
            sys.stderr.write(f"\n[LOGIN_ERROR] Password mismatch for user: {user.phone or user.email}\n")
            sys.stderr.flush()
            raise serializers.ValidationError(INVALID_CREDENTIALS_MSG)

        if not user.is_rider:
            sys.stderr.write(f"\n[LOGIN_ERROR] User {user.phone} is not a rider (role: {user.role})\n")
            sys.stderr.flush()
            raise serializers.ValidationError("Not a rider account")

        attrs["user"] = user
        return attrs


class DriverLoginSerializer(serializers.Serializer):
    phone = serializers.CharField()  # This field can accept phone or email
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        value = attrs["phone"]
        try:
            user = User.objects.filter(Q(phone=value) | Q(email=value)).first()
            if not user:
                raise serializers.ValidationError(INVALID_CREDENTIALS_MSG)
        except Exception:
            raise serializers.ValidationError(INVALID_CREDENTIALS_MSG)

        if not user.check_password(attrs["password"]):
            raise serializers.ValidationError(INVALID_CREDENTIALS_MSG)

        if not user.is_driver:
            raise serializers.ValidationError("Not a driver account")

        attrs["user"] = user
        return attrs


class AdminLoginSerializer(serializers.Serializer):
    username = serializers.CharField(required=False)
    email = serializers.CharField(required=False)
    phone = serializers.CharField(required=False)  # Added support for phone key
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        username = attrs.get("username")
        email = attrs.get("email")
        phone = attrs.get("phone")
        password = attrs.get("password")

        user = None
        # Try all identifiers
        identifier = phone or username or email
        if identifier:
            try:
                user_obj = User.objects.filter(Q(username=identifier) | Q(email=identifier) | Q(phone=identifier)).first()
                if user_obj:
                    user = authenticate(username=user_obj.username, password=password)
            except Exception:
                pass

        if not user:
            raise serializers.ValidationError(INVALID_CREDENTIALS_MSG)

        if not user.is_admin:
            raise serializers.ValidationError("Admin access only")

        attrs["user"] = user
        return attrs


class UserSerializer(serializers.ModelSerializer):
    is_verified = serializers.SerializerMethodField()
    completed_rides = serializers.SerializerMethodField()
    avg_rating = serializers.SerializerMethodField()
    level = serializers.SerializerMethodField()
    wallet_balance = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "phone",
            "role",
            "first_name",
            "last_name",
            "email",  # added email
            "gender", # added gender
            "address", # added primary address
            "is_verified",
            "expo_push_token",
            "completed_rides",
            "avg_rating",
            "level",
            "referral_code",
            "wallet_balance",
        ]

    def get_wallet_balance(self, obj):
        from apps.users.models import Wallet
        wallet, _ = Wallet.objects.get_or_create(user=obj)
        return wallet.balance


    def get_is_verified(self, obj):
        if obj.role == "driver":
            driver = getattr(obj, "driver", None)
            return driver.is_verified if driver else False
        return True

    def get_completed_rides(self, obj):
        if obj.role == "driver" and hasattr(obj, "driver"):
            from apps.drivers.models import DriverStats

            stats, _ = DriverStats.objects.get_or_create(driver=obj.driver)
            return stats.completed_rides
        return 0

    def get_avg_rating(self, obj):
        if obj.role == "driver" and hasattr(obj, "driver"):
            from apps.drivers.models import DriverStats

            stats, _ = DriverStats.objects.get_or_create(driver=obj.driver)
            return stats.avg_rating
        return 5.0

    def get_level(self, obj):
        if obj.role == "driver" and hasattr(obj, "driver"):
            return obj.driver.level
        return "NORMAL"

class SavedAddressSerializer(serializers.ModelSerializer):
    class Meta:
        from apps.users.models import SavedAddress
        model = SavedAddress
        fields = ["id", "label", "address", "latitude", "longitude", "created_at"]
        read_only_fields = ["id", "created_at"]


class StaticContentSerializer(serializers.ModelSerializer):
    class Meta:
        from apps.users.models import StaticContent
        model = StaticContent
        fields = ["key", "title", "content", "updated_at"]
        read_only_fields = ["updated_at"]
class WalletSerializer(serializers.ModelSerializer):
    class Meta:
        from apps.users.models import Wallet
        model = Wallet
        fields = ["balance", "updated_at"]

class ReferralSerializer(serializers.ModelSerializer):
    class Meta:
        from apps.users.models import User
        model = User
        fields = ["id", "first_name", "first_name", "date_joined"]
