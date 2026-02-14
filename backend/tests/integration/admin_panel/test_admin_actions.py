import pytest
from apps.users.models import User
from apps.drivers.models import Driver
from rest_framework.test import APIClient

@pytest.mark.django_db
def test_admin_suspend_driver(client):
    # Setup Admin
    admin = User.objects.create_user(username="admin_integ", role="admin")
    
    # Setup Driver
    driver_user = User.objects.create_user(username="bad_driver", role="driver")
    driver = driver_user.driver
    
    api_client = APIClient()
    api_client.force_authenticate(user=admin)
    
    # 1. List Drivers
    resp = api_client.get("/api/drivers/admin/drivers/")
    assert resp.status_code == 200
    # Response is list
    assert isinstance(resp.data, list)
    assert len(resp.data) >= 1
    
    # 2. Suspend Driver
    payload = {"driver_id": driver.id, "action": "suspend"}
    resp = api_client.post("/api/drivers/admin/drivers/actions/", payload)
    
    assert resp.status_code == 200
    assert resp.data["success"] is True
    
    driver.refresh_from_db()
    # Check stats suspension
    assert driver.stats.is_suspended is True
    # Check forced offline
    assert driver.status == "OFFLINE"

@pytest.mark.django_db
def test_non_admin_blocked(client):
    user = User.objects.create_user(username="regular", role="rider")
    api_client = APIClient()
    api_client.force_authenticate(user=user)
    
    resp = api_client.get("/api/drivers/admin/drivers/")
    assert resp.status_code == 403
