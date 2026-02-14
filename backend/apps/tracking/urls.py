from django.urls import path
from .views import UpdateLocationView

urlpatterns = [
    path("update-location/", UpdateLocationView.as_view(), name="update-location"),
]
