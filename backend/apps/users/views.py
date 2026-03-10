from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .serializers import (
    AdminLoginSerializer,
    DriverLoginSerializer,
    RegisterSerializer,
    RiderLoginSerializer,
    UserSerializer,
)


def jwt_tokens(user):
    refresh = RefreshToken.for_user(user)
    return {
        "refresh": str(refresh),
        "access": str(refresh.access_token),
    }


class RegisterView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # Send Welcome Email
        if user.email:
            from django.db import transaction

            from apps.notifications.models import Notification

            transaction.on_commit(
                lambda: Notification.objects.create(
                    user=user,
                    channel="email",
                    type="WELCOME_EMAIL",
                    payload={
                        "subject": "Welcome to Uber Clone!",
                        "body": f"Hi {user.first_name}, thanks for joining us!",
                        "html": f"<h1>Welcome {user.first_name}!</h1><p>We're glad to have you on board.</p>",
                    },
                )
            )

        return Response(UserSerializer(user).data, status=201)


class RiderLoginView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        import sys

        sys.stderr.write(f"\n--- LOGIN ATTEMPT ---\nData: {request.data}\n")
        sys.stderr.flush()
        serializer = RiderLoginSerializer(data=request.data)
        if not serializer.is_valid():
            sys.stderr.write(f"Errors: {serializer.errors}\n")
            sys.stderr.flush()
            return Response(serializer.errors, status=400)
        user = serializer.validated_data["user"]
        sys.stderr.write(f"Success for user: {user.phone}\n")
        sys.stderr.flush()
        data = jwt_tokens(user)
        data["user"] = UserSerializer(user).data
        return Response(data)


class DriverLoginView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = DriverLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        data = jwt_tokens(user)
        data["user"] = UserSerializer(user).data
        return Response(data)


class AdminLoginView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = AdminLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        data = jwt_tokens(user)
        data["user"] = UserSerializer(user).data
        return Response(data)


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from .serializers import UserSerializer

        user_data = UserSerializer(request.user).data
        print(
            f"[DEBUG] MeView for {request.user.phone}: Role={request.user.role}, Data={user_data}"
        )
        return Response(user_data)


class UpdatePushTokenView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        token = request.data.get("token")
        if not token:
            return Response({"error": "Token is required"}, status=400)

        request.user.expo_push_token = token
        request.user.save(update_fields=["expo_push_token"])
        return Response({"status": "Token updated"})
