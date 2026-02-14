from django.urls import path
from .views import AdminOverviewView, AdminLiveMapSnapshot

urlpatterns = [
    path("overview/", AdminOverviewView.as_view()),
    path("live-map/snapshot/", AdminLiveMapSnapshot.as_view()),

]

