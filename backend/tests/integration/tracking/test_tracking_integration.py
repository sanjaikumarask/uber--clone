import pytest
from apps.users.models import User
from apps.drivers.models import Driver
from rest_framework.test import APIClient
from unittest.mock import patch

@pytest.mark.django_db
@patch("asgiref.sync.async_to_sync")
@patch("channels.layers.get_channel_layer")
def test_update_location_view(mock_get_layer, mock_async_to_sync, client):
    # Setup Driver
    user = User.objects.create_user(username="tracker", password="p", role="driver")
    # Signal creates driver
    driver = user.driver
    driver.status = "ONLINE"
    driver.save()
    
    api_client = APIClient()
    api_client.force_authenticate(user=user)
    
    # Call Endpoint
    # /api/drivers/location/ is standard path if mapped
    # Assuming /api/drivers/ prefix for drivers app
    payload = {"lat": 12.9716, "lng": 77.5946}
    resp = api_client.post("/api/drivers/location/", payload)
    
    assert resp.status_code == 200
    
    # Verify DB
    driver.refresh_from_db()
    assert driver.last_lat == 12.9716
    assert driver.last_lng == 77.5946
    
    # Verify Broadcast
    mock_get_layer.assert_called_once()
    mock_async_to_sync.assert_called_once() 
