from unittest.mock import MagicMock, patch
from rest_framework.test import APIRequestFactory, force_authenticate
from apps.admin_dashboard.views import AdminOverviewView, AdminLiveMapSnapshot

@patch("apps.admin_dashboard.views.Driver")
@patch("apps.admin_dashboard.views.Ride")
def test_admin_overview_metrics(mock_Ride_cls, mock_Driver_cls):
    # Setup Mocks
    # Driver.objects.filter().count()
    mock_Driver_cls.objects.filter.return_value.count.return_value = 10
    
    # Ride.objects.filter().count()
    mock_Ride_cls.objects.filter.return_value.count.return_value = 5

    factory = APIRequestFactory()
    request = factory.get('/api/admin/overview/')
    
    # Mock Admin User
    user = MagicMock()
    user.is_authenticated = True
    user.is_admin = True
    
    force_authenticate(request, user=user)
    
    view = AdminOverviewView.as_view()
    response = view(request)
    
    assert response.status_code == 200
    assert response.data['online_drivers'] == 10
    assert response.data['active_rides'] == 5
    # Verification of other fields follows same pattern (mock returns same count for all filters unless distinct side_effect used)

@patch("apps.admin_dashboard.views.Driver")
@patch("apps.admin_dashboard.views.Ride")
def test_admin_live_map_snapshot(mock_Ride_cls, mock_Driver_cls):
    # Setup Driver Mock
    mock_driver_instance = MagicMock()
    mock_driver_instance.id = 1
    mock_driver_instance.last_lat = 10.0
    mock_driver_instance.last_lng = 20.0
    mock_driver_instance.status = "ONLINE"
    mock_driver_instance.user.phone = "12345"
    
    # Driver.objects.exclude(...) returns iterator of drivers
    mock_Driver_cls.objects.exclude.return_value = [mock_driver_instance]

    # Setup Ride Mock
    mock_ride_instance = MagicMock()
    mock_ride_instance.id = 100
    mock_ride_instance.status = "SEARCHING"
    mock_ride_instance.pickup_lat = 11.0
    mock_ride_instance.pickup_lng = 21.0
    mock_ride_instance.drop_lat = 12.0
    mock_ride_instance.drop_lng = 22.0
    mock_ride_instance.driver_id = None
    
    # Ride.objects.filter(...) returns iterator of rides
    mock_Ride_cls.objects.filter.return_value = [mock_ride_instance]

    factory = APIRequestFactory()
    request = factory.get('/api/admin/live-map/')
    
    # Mock Admin User
    user = MagicMock()
    user.is_authenticated = True
    user.is_admin = True
    
    force_authenticate(request, user=user)
    
    view = AdminLiveMapSnapshot.as_view()
    response = view(request)
    
    assert response.status_code == 200
    
    # Check Drivers Data
    drivers_data = response.data['drivers']
    assert len(drivers_data) == 1
    assert drivers_data[0]['id'] == 1
    assert drivers_data[0]['lat'] == 10.0
    
    # Check Rides Data
    rides_data = response.data['rides']
    assert len(rides_data) == 1
    assert rides_data[0]['id'] == 100
    assert rides_data[0]['status'] == "SEARCHING"
    assert rides_data[0]['pickup']['lat'] == 11.0
