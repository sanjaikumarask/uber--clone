from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    AdminLoginView,
    DriverLoginView,
    MeView,
    RegisterView,
    RiderLoginView,
    UpdatePushTokenView,
)

urlpatterns = [
    path("register/", RegisterView.as_view()),
    path("login/", RiderLoginView.as_view()),  # rider
    path("driver-login/", DriverLoginView.as_view()),  # driver
    path("admin-login/", AdminLoginView.as_view()),  # admin
    path("token/refresh/", TokenRefreshView.as_view()),  # 🔥 NEW: JWT Token refresh
    path("me/", MeView.as_view()),
    path("push-token/update/", UpdatePushTokenView.as_view()),
]
