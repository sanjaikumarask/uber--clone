from django.urls import path
from .views import (
    RegisterView,
    RiderLoginView,
    DriverLoginView,
    AdminLoginView,
    MeView,
    UpdatePushTokenView,
)

from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    path("register/", RegisterView.as_view()),
    path("login/", RiderLoginView.as_view()),        # rider
    path("driver-login/", DriverLoginView.as_view()), # driver
    path("admin-login/", AdminLoginView.as_view()),  # admin
    path("token/refresh/", TokenRefreshView.as_view()), # 🔥 NEW: JWT Token refresh
    path("me/", MeView.as_view()),
    path("push-token/update/", UpdatePushTokenView.as_view()),
]
