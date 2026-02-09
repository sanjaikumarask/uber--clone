from django.urls import path
from .views import (
    LoginView,
    RefreshTokenView,
    RegisterView,
    MeView,
    RiderProfileView,
    DriverProfileView,
    AdminUsersListView,
)

urlpatterns = [
    # Auth
    path("login/", LoginView.as_view()),
    path("refresh/", RefreshTokenView.as_view()),
    path("register/", RegisterView.as_view()),

    # Profiles
    path("me/", MeView.as_view()),
    path("rider/profile/", RiderProfileView.as_view()),
    path("driver/profile/", DriverProfileView.as_view()),

    # Admin
    path("admin/users/", AdminUsersListView.as_view()),
]
