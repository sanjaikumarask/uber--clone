from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated

from django.contrib.auth import get_user_model

from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

from apps.users.permissions import IsRider, IsDriver, IsAdmin
from .serializers import (
    UserRegisterSerializer,
    CustomTokenObtainPairSerializer,
)

User = get_user_model()


# ======================================================
# 🔐 AUTH (JWT)
# ======================================================

class LoginView(TokenObtainPairView):
    """
    POST /api/users/login/
    """
    permission_classes = [AllowAny]
    serializer_class = CustomTokenObtainPairSerializer


class RefreshTokenView(TokenRefreshView):
    """
    POST /api/users/refresh/
    """
    permission_classes = [AllowAny]


# ======================================================
# 📝 REGISTER
# ======================================================

class RegisterView(APIView):
    """
    POST /api/users/register/
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = UserRegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.save()

        return Response(
            {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "role": user.role,
            },
            status=status.HTTP_201_CREATED,
        )


# ======================================================
# 👤 COMMON PROFILE (ANY AUTH USER)
# ======================================================

class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        return Response(
            {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "role": user.role,
                "is_active": user.is_active,
            },
            status=status.HTTP_200_OK,
        )


# ======================================================
# 🧍 RIDER ONLY
# ======================================================

class RiderProfileView(APIView):
    permission_classes = [IsRider]

    def get(self, request):
        return Response(
            {
                "id": request.user.id,
                "username": request.user.username,
                "role": request.user.role,
            }
        )


# ======================================================
# 🚗 DRIVER ONLY
# ======================================================

class DriverProfileView(APIView):
    permission_classes = [IsDriver]

    def get(self, request):
        return Response(
            {
                "id": request.user.id,
                "username": request.user.username,
                "role": request.user.role,
            }
        )


# ======================================================
# 👑 ADMIN ONLY
# ======================================================

class AdminUsersListView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        users = User.objects.all().order_by("-date_joined")

        return Response(
            [
                {
                    "id": u.id,
                    "username": u.username,
                    "email": u.email,
                    "role": u.role,
                    "is_active": u.is_active,
                }
                for u in users
            ]
        )
