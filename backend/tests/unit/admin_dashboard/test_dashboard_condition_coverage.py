import pytest
from unittest.mock import patch, MagicMock
from decimal import Decimal
from django.utils.timezone import now
from datetime import timedelta
from rest_framework import status
from rest_framework.test import APIClient
import uuid

from apps.drivers.models import Driver
from apps.rides.models import Ride
from apps.payments.models import Payment, Payout
from apps.admin_dashboard.models import SystemLog
from apps.supports.models import SupportTicket, Emergency
from apps.rides.fare_models import FareConfig

@pytest.fixture
def api_client():
    return APIClient()

@pytest.fixture
def admin_user(django_user_model):
    uid = uuid.uuid4().hex[:8]
    return django_user_model.objects.create_user(
        username=f"admin_cov_{uid}", password="pwd", role="admin"
    )

@pytest.fixture
def normal_user(django_user_model):
    uid = uuid.uuid4().hex[:8]
    return django_user_model.objects.create_user(
        username=f"user_cov_{uid}", password="pwd", role="rider"
    )

@pytest.fixture
def driver_user(django_user_model):
    uid = uuid.uuid4().hex[:8]
    return django_user_model.objects.create_user(
        username=f"drvr_cov_{uid}", password="pwd", role="driver", phone=f"+100{uid[:6]}"
    )

@pytest.fixture
def driver_profile(driver_user):
    profile, _ = Driver.objects.get_or_create(
        user=driver_user,
        defaults={'status': Driver.Status.ONLINE, 'level': Driver.Level.NORMAL, 'is_verified': True}
    )
    profile.status = Driver.Status.ONLINE
    profile.is_verified = True
    profile.save()
    return profile

@pytest.fixture
def admin_client(api_client, admin_user):
    api_client.force_authenticate(user=admin_user)
    return api_client

@pytest.fixture
def fare_config():
    return FareConfig.objects.create(
        vehicle_type="go", base_fare=Decimal("50.00"), per_km_rate=Decimal("10.00"), per_min_rate=Decimal("1.50")
    )

@pytest.mark.django_db
class TestAdminDashboardCoverage:
    
    @pytest.mark.parametrize("is_auth, is_admin, expected_status", [
        (False, False, status.HTTP_401_UNAUTHORIZED),
        (True, False, status.HTTP_403_FORBIDDEN),
        (True, True, status.HTTP_200_OK),
    ])
    def test_admin_permissions(self, api_client, normal_user, admin_user, is_auth, is_admin, expected_status):
        if is_auth and not is_admin:
            api_client.force_authenticate(user=normal_user)
        elif is_auth and is_admin:
            api_client.force_authenticate(user=admin_user)
            
        response = api_client.get('/api/admin/fare-config/')
        assert response.status_code == expected_status

    def test_fare_config_get_pk(self, admin_client, fare_config):
        response = admin_client.get(f'/api/admin/fare-config/{fare_config.pk}/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data["vehicle_type"] == "go"

    def test_fare_config_patch_invalid(self, admin_client, fare_config):
        response = admin_client.patch(f'/api/admin/fare-config/{fare_config.pk}/', {"base_fare": "INVALID"})
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_flare_config_patch_valid(self, admin_client, fare_config):
        response = admin_client.patch(f'/api/admin/fare-config/{fare_config.pk}/', {"base_fare": "60.00"})
        assert response.status_code == status.HTTP_200_OK
        assert response.data["base_fare"] == "60.00"

    def test_payment_status_stale(self, admin_client, normal_user):
        Payment.objects.create(
            user=normal_user, amount=Decimal("100.00"), status=Payment.Status.CREATED
        )
        Payment.objects.filter(status=Payment.Status.CREATED).update(created_at=now() - timedelta(minutes=45))

        response = admin_client.get('/api/admin/payments/status/')
        assert response.status_code == status.HTTP_200_OK
        
        alerts = response.data["alerts"]
        stale_alert = next((a for a in alerts if a["type"] == "STALE_PAYMENTS"), None)
        assert stale_alert is not None

    def test_payment_status_high_failure(self, admin_client, normal_user):
        for _ in range(5):
            Payment.objects.create(user=normal_user, amount=Decimal("10.00"), status=Payment.Status.FAILED)
        Payment.objects.create(user=normal_user, amount=Decimal("10.00"), status=Payment.Status.CAPTURED)

        response = admin_client.get('/api/admin/payments/status/')
        assert response.status_code == status.HTTP_200_OK
        
        alerts = response.data["alerts"]
        fail_alert = next((a for a in alerts if a["type"] == "HIGH_FAILURE_RATE"), None)
        assert fail_alert is not None

    def test_system_alerts_stuck_ride(self, admin_client, normal_user, driver_profile):
        ride = Ride.objects.create(
            rider=normal_user, status=Ride.Status.ONGOING, driver=driver_profile,
            pickup_lat=12.0, pickup_lng=77.0, drop_lat=12.1, drop_lng=77.1
        )
        Ride.objects.filter(id=ride.id).update(updated_at=now() - timedelta(minutes=50))
        
        response = admin_client.get('/api/admin/alerts/')
        assert response.status_code == status.HTTP_200_OK
        
        logs = SystemLog.objects.filter(type=SystemLog.LogType.RIDE_STUCK, metadata__ride_id=ride.id)
        assert logs.exists()

    @pytest.mark.parametrize("status_filter,expected_count", [
        ("ONLINE", 1),
        ("OFFLINE", 0),
        ("INVALID", 0),
        (None, 1),
    ])
    def test_driver_list_filters(self, admin_client, driver_profile, status_filter, expected_count):
        url = '/api/admin/drivers/'
        if status_filter:
            url += f'?status={status_filter}'
        response = admin_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == expected_count

    @pytest.mark.parametrize("action,expected_verified", [
        ("approve", True),
        ("reject", False),
        ("block", False),
    ])
    def test_driver_action(self, admin_client, driver_profile, action, expected_verified):
        driver_profile.is_verified = not expected_verified
        driver_profile.save()
        
        response = admin_client.post(f'/api/admin/drivers/{driver_profile.id}/action/', {"action": action})
        assert response.status_code == status.HTTP_200_OK
        driver_profile.refresh_from_db()
        assert driver_profile.is_verified == expected_verified

    def test_live_map_snapshot(self, admin_client, normal_user, driver_profile):
        driver_profile.last_lat = 12.0
        driver_profile.last_lng = 77.0
        driver_profile.save()
        
        Ride.objects.create(
            rider=normal_user, driver=driver_profile, status=Ride.Status.ONGOING,
            pickup_lat=12.0, pickup_lng=77.0, drop_lat=12.1, drop_lng=77.1
        )
        
        response = admin_client.get('/api/admin/live-map/snapshot/')
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["drivers"]) == 1
        assert len(response.data["rides"]) == 1

    def test_overview_redis_fail(self, admin_client):
        from django.core.cache import cache
        original_set = cache.set
        
        def custom_set(*args, **kwargs):
            if args and args[0] == "admin:health:ping":
                raise Exception("Redis completely down")
            return original_set(*args, **kwargs)
            
        with patch('django.core.cache.cache.set', side_effect=custom_set):
            response = admin_client.get('/api/admin/overview/')
            assert response.status_code == status.HTTP_200_OK
            assert response.data["system_health"]["redis"]["ok"] is False

    @pytest.mark.parametrize("action,start_status,expected_code,expected_end_status", [
        ("approve", Payout.Status.REQUESTED, 200, Payout.Status.PROCESSING),
        ("approve", Payout.Status.PAID, 400, Payout.Status.PAID),
        ("reject", Payout.Status.REQUESTED, 200, Payout.Status.FAILED),
        ("reject", Payout.Status.PAID, 400, Payout.Status.PAID),
        ("resolve", Payout.Status.REQUESTED, 200, Payout.Status.PAID),
        ("invalid", Payout.Status.REQUESTED, 400, Payout.Status.REQUESTED),
    ])
    @patch('apps.payments.tasks.execute_driver_payout.delay')
    def test_payout_actions(self, mock_task, admin_client, driver_user, action, start_status, expected_code, expected_end_status):
        payout = Payout.objects.create(
            driver=driver_user, amount=Decimal("100"), fee=Decimal("0"), net_amount=Decimal("100"),
            status=start_status, reference=f"ref_{uuid.uuid4().hex[:8]}"
        )
        response = admin_client.post(f'/api/admin/payout/{action}/{payout.id}/')
        assert response.status_code == expected_code
        payout.refresh_from_db()
        assert payout.status == expected_end_status

    def test_admin_tickets_view(self, admin_client, normal_user, driver_profile):
        ride = Ride.objects.create(
            rider=normal_user, driver=driver_profile, status=Ride.Status.ONGOING,
            pickup_lat=12.0, pickup_lng=77.0, drop_lat=12.1, drop_lng=77.1
        )
        ticket = SupportTicket.objects.create(
            user=normal_user, reason="APP_ISSUE", description="App crashed", 
            status=SupportTicket.Status.OPEN, ride=ride
        )
        emergency = Emergency.objects.create(
            user=normal_user, lat=12.0, lng=77.0, status=Emergency.Status.ACTIVE, ride=ride
        )
        response = admin_client.get('/api/admin/tickets/')
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["tickets"]) == 1
        assert response.data["tickets"][0]["id"] == ticket.id
        assert len(response.data["emergencies"]) == 1
        assert response.data["emergencies"][0]["id"] == emergency.id
        assert "user_name" in response.data["tickets"][0]

    @patch('apps.rides.admin_views.service_cancel_ride')
    def test_admin_resolve_ride(self, mock_cancel, admin_client, normal_user):
        ride = Ride.objects.create(
            rider=normal_user, status=Ride.Status.ONGOING,
            pickup_lat=12.0, pickup_lng=77.0, drop_lat=12.1, drop_lng=77.1
        )
        response = admin_client.post('/api/admin/resolve-ride/', {"ride_id": ride.id, "action": "CANCEL"})
        assert response.status_code == status.HTTP_200_OK
        mock_cancel.assert_called_once()
        
    @patch('redis.Redis.from_url')
    def test_admin_system_logs_success(self, mock_redis_from_url, admin_client):
        mock_instance = MagicMock()
        mock_instance.lrange.return_value = ['{"sys": "log"}', "INVALID_JSON"]
        mock_redis_from_url.return_value = mock_instance
        response = admin_client.get('/api/admin/logs/')
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1

    @patch('redis.Redis.from_url')
    def test_admin_system_logs_failure(self, mock_redis_from_url, admin_client):
        mock_redis_from_url.side_effect = Exception("Connection Failed")
        response = admin_client.get('/api/admin/logs/')
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
