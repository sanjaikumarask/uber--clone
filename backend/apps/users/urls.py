from django.urls import path
from .views import (
    RegisterView,
    RiderLoginView,
    DriverLoginView,
    AdminLoginView,
    MeView,
)

urlpatterns = [
    path("register/", RegisterView.as_view()),
    path("login/", RiderLoginView.as_view()),        # rider
    path("driver-login/", DriverLoginView.as_view()), # driver
    path("admin-login/", AdminLoginView.as_view()),  # admin
    path("me/", MeView.as_view()),
]
