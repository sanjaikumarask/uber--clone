import pytest
from decimal import Decimal
from unittest.mock import patch
from django.urls import reverse

from rest_framework import status
from apps.users.models import User
from apps.rides.models import Ride
from apps.rides.fare_models import FareConfig
from apps.drivers.models import Driver

from apps.payments.models import Payment, LedgerEntry, Payout

@pytest.fixture
def admin_user():
    return User.objects.create_user(username="admin_ext", password="password", phone="+917777777777", role="admin")


@pytest.fixture
def admin_client(api_client, admin_user):
    api_client.force_authenticate(user=admin_user)
    return api_client

@pytest.mark.django_db
class TestAdminActionsExtended:

    def test_admin_ride_action_cancel(self, admin_client, rider_user, driver_user):
        driver, _ = Driver.objects.get_or_create(user=driver_user)
        ride = Ride.objects.create(
            rider=rider_user, 
            driver=driver,
            status=Ride.Status.ASSIGNED,
            pickup_lat=12.0, pickup_lng=77.0,
            drop_lat=12.1, drop_lng=77.1,
            base_fare=100
        )
        
        # Capture payment first to test refund
        Payment.objects.create(
            user=rider_user,
            ride_id=ride.id,
            amount=100,
            status=Payment.Status.CAPTURED,
            gateway="simulation"
        )

        url = "/api/rides/admin/rides/actions/"
        payload = {
            "ride_id": ride.id,
            "action": "cancel",
            "refund_amount": 50,
            "compensate_driver_amount": 25
        }
        response = admin_client.post(url, payload, format='json')
        assert response.status_code == status.HTTP_200_OK
        
        ride.refresh_from_db()
        assert ride.status == Ride.Status.CANCELLED
        assert LedgerEntry.objects.filter(ride_id=ride.id, reason=LedgerEntry.Reason.REFUND).exists()
        assert LedgerEntry.objects.filter(ride_id=ride.id, reason=LedgerEntry.Reason.INCENTIVE).exists()

    def test_admin_ride_action_reassign(self, admin_client, rider_user, driver_user):

        driver, _ = Driver.objects.get_or_create(user=driver_user)
        driver.status = Driver.Status.BUSY
        driver.save()
        
        ride = Ride.objects.create(
            rider=rider_user, 
            driver=driver,
            status=Ride.Status.ASSIGNED,
            pickup_lat=12.0, pickup_lng=77.0,
            drop_lat=12.1, drop_lng=77.1,
            base_fare=100
        )
        
        url = "/api/rides/admin/rides/actions/"
        payload = {
            "ride_id": ride.id,
            "action": "reassign"
        }
        response = admin_client.post(url, payload, format='json')
        assert response.status_code == status.HTTP_200_OK
        
        ride.refresh_from_db()
        assert ride.status == Ride.Status.SEARCHING
        assert ride.driver is None
        
        driver.refresh_from_db()
        assert driver.status == Driver.Status.ONLINE

    def test_admin_resolve_ride_complex(self, admin_client, rider_user, driver_user):
        driver, _ = Driver.objects.get_or_create(user=driver_user)
        ride = Ride.objects.create(
            rider=rider_user, 
            driver=driver,
            status=Ride.Status.COMPLETED,
            pickup_lat=12.0, pickup_lng=77.0,
            drop_lat=12.1, drop_lng=77.1,
            base_fare=100,
            final_fare=150
        )
        
        url = "/api/admin/resolve-ride/"
        payload = {
            "ride_id": ride.id,
            "action": "RESOLVE",
            "reason": "Bad experience",
            "refund_amount": 30,
            "driver_compensation": 20,
            "penalty_amount": 10,
            "waive_fee": True
        }
        
        # For waive_fee to work, we need a platform commission entry
        LedgerEntry.objects.create(
            user=rider_user, # dummy, usually platform user
            ride_id=ride.id,
            amount=15,
            entry_type=LedgerEntry.Type.CREDIT,
            reason=LedgerEntry.Reason.PLATFORM_COMMISSION
        )

        response = admin_client.post(url, payload, format='json')
        assert response.status_code == status.HTTP_200_OK
        assert response.data["success"] is True
        
        # Verify ledger entries
        assert LedgerEntry.objects.filter(ride_id=ride.id, reason=LedgerEntry.Reason.REFUND).exists()
        assert LedgerEntry.objects.filter(ride_id=ride.id, reason=LedgerEntry.Reason.INCENTIVE).exists()
        assert LedgerEntry.objects.filter(ride_id=ride.id, reason=LedgerEntry.Reason.PENALTY).exists()


    def test_admin_rides_list(self, admin_client, rider_user):
        Ride.objects.create(
            rider=rider_user, 
            pickup_lat=12.0, pickup_lng=77.0,
            drop_lat=12.1, drop_lng=77.1,
            base_fare=100
        )
        url = "/api/rides/admin/rides/"
        response = admin_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 1

    def test_admin_ride_action_compensate(self, admin_client, rider_user, driver_user):
        driver, _ = Driver.objects.get_or_create(user=driver_user)
        ride = Ride.objects.create(
            rider=rider_user, 
            driver=driver,
            status=Ride.Status.COMPLETED,
            pickup_lat=12.0, pickup_lng=77.0,
            drop_lat=12.1, drop_lng=77.1,
            base_fare=100
        )
        
        url = "/api/rides/admin/rides/actions/"
        payload = {
            "ride_id": ride.id,
            "action": "compensate_driver",
            "amount": 50,
            "reason": "Top performance"
        }
        response = admin_client.post(url, payload, format='json')
        assert response.status_code == status.HTTP_200_OK
        assert LedgerEntry.objects.filter(ride_id=ride.id, reason=LedgerEntry.Reason.INCENTIVE).exists()

    def test_admin_ride_action_missing_id(self, admin_client):
        url = "/api/rides/admin/rides/actions/"
        response = admin_client.post(url, {"action": "cancel"}, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["error"] == "ride_id is required"

    def test_admin_ride_action_invalid_action(self, admin_client, rider_user):
        ride = Ride.objects.create(rider=rider_user, pickup_lat=0, pickup_lng=0, drop_lat=0, drop_lng=0, base_fare=0)
        url = "/api/rides/admin/rides/actions/"
        response = admin_client.post(url, {"ride_id": ride.id, "action": "fly_to_moon"}, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["error"] == "Invalid action"

    def test_admin_ride_action_not_found(self, admin_client):
        url = "/api/rides/admin/rides/actions/"
        response = admin_client.post(url, {"ride_id": 999999, "action": "cancel"}, format='json')
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_admin_ride_action_refund_no_payment(self, admin_client, rider_user):
        ride = Ride.objects.create(rider=rider_user, pickup_lat=0, pickup_lng=0, drop_lat=0, drop_lng=0, base_fare=100)
        url = "/api/rides/admin/rides/actions/"
        response = admin_client.post(url, {"ride_id": ride.id, "action": "refund"}, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "No captured payment found" in response.data["error"]

    def test_admin_resolve_ride_errors(self, admin_client):
        url = "/api/admin/resolve-ride/"
        # Missing ID
        response = admin_client.post(url, {"action": "RESOLVE"}, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        
        # Non-existent ride
        response = admin_client.post(url, {"ride_id": 999999, "action": "RESOLVE"}, format='json')
        assert response.status_code == 404

    def test_admin_resolve_ride_automated_rules(self, admin_client, rider_user, driver_user):
        driver, _ = Driver.objects.get_or_create(user=driver_user)
        from apps.drivers.models import DriverStats
        DriverStats.objects.get_or_create(driver=driver)
        
        ride = Ride.objects.create(
            rider=rider_user, driver=driver, status=Ride.Status.COMPLETED,
            pickup_lat=0, pickup_lng=0, drop_lat=0, drop_lng=0, base_fare=100
        )
        
        url = "/api/admin/resolve-ride/"
        payload = {
            "ride_id": ride.id,
            "action": "RESOLVE",
            "reason": "Driver not moving",
        }
        response = admin_client.post(url, payload, format='json')
        assert response.status_code == 200
        assert LedgerEntry.objects.filter(ride_id=ride.id, reason=LedgerEntry.Reason.PENALTY).exists()

    def test_admin_resolve_ride_waive_fee(self, admin_client, rider_user, driver_user):
        driver, _ = Driver.objects.get_or_create(user=driver_user)
        ride = Ride.objects.create(
            rider=rider_user, driver=driver, status=Ride.Status.COMPLETED,
            pickup_lat=0, pickup_lng=0, drop_lat=0, drop_lng=0, base_fare=100
        )
        
        # Create platform commission
        LedgerEntry.objects.create(
            user=rider_user, # dummy
            ride_id=ride.id,
            amount=20,
            entry_type=LedgerEntry.Type.CREDIT,
            reason=LedgerEntry.Reason.PLATFORM_COMMISSION
        )
        
        # Mock captured payment so _waive_platform_fee continues
        Payment.objects.create(
            user=rider_user, ride_id=ride.id, amount=100, status=Payment.Status.CAPTURED, gateway="sim"
        )

        url = "/api/admin/resolve-ride/"
        payload = {
            "ride_id": ride.id,
            "action": "RESOLVE",
            "waive_fee": True
        }
        response = admin_client.post(url, payload, format='json')
        assert response.status_code == 200
        # Should have a DEBIT for PLATFORM_COMMISSION (waive) and a CREDIT for driver
        assert LedgerEntry.objects.filter(ride_id=ride.id, entry_type=LedgerEntry.Type.DEBIT, reason=LedgerEntry.Reason.PLATFORM_COMMISSION).exists()
        assert LedgerEntry.objects.filter(ride_id=ride.id, entry_type=LedgerEntry.Type.CREDIT, reason=LedgerEntry.Reason.OTHER).exists()

    def test_admin_fare_config_detail(self, admin_client):
        config, _ = FareConfig.objects.get_or_create(vehicle_type="moto_det", defaults={"base_fare": 45})
        url = f"/api/admin/fare-config/{config.id}/"
        response = admin_client.get(url)
        assert response.status_code == 200
        assert response.data["vehicle_type"] == "moto_det"


    def test_admin_payment_status_alerts_high_failure(self, admin_client, rider_user):
        # Create payments: 1 success, 4 failed -> 80% failure rate
        Payment.objects.create(user=rider_user, amount=10, status=Payment.Status.CAPTURED, gateway_order_id="O1")
        for i in range(2, 6):
            Payment.objects.create(user=rider_user, amount=10, status=Payment.Status.FAILED, gateway_order_id=f"O{i}")
        
        url = "/api/admin/payments/status/"
        response = admin_client.get(url)
        assert response.status_code == 200
        assert any(a["type"] == "HIGH_FAILURE_RATE" for a in response.data["alerts"])

    def test_admin_alerts_stuck_rides(self, admin_client, rider_user):
        from django.utils.timezone import now
        from datetime import timedelta
        ride = Ride.objects.create(
            rider=rider_user, status=Ride.Status.ONGOING,
            pickup_lat=0, pickup_lng=0, drop_lat=0, drop_lng=0, base_fare=100
        )
        # Manually backdate updated_at using update
        Ride.objects.filter(id=ride.id).update(updated_at=now() - timedelta(minutes=50))
        
        url = "/api/admin/alerts/"
        response = admin_client.get(url)
        assert response.status_code == 200
        # This view creates SystemLog entries for stuck rides
        from apps.admin_dashboard.models import SystemLog
        assert SystemLog.objects.filter(type=SystemLog.LogType.RIDE_STUCK, metadata__ride_id=ride.id).exists()

    def test_admin_overview_redis_fail(self, admin_client):
        from apps.admin_dashboard.views import AdminOverviewView
        orig_throttles = AdminOverviewView.throttle_classes
        AdminOverviewView.throttle_classes = []
        try:
            with patch('django.core.cache.cache.set', side_effect=Exception("Redis Down")):
                url = "/api/admin/overview/"
                response = admin_client.get(url)
                assert response.status_code == 200
                assert response.data["system_health"]["redis"]["ok"] is False
        finally:
            AdminOverviewView.throttle_classes = orig_throttles


    @patch('redis.Redis.from_url')
    def test_admin_system_logs_fail(self, mock_redis_url, admin_client):
        mock_redis_url.side_effect = Exception("Connection Error")
        url = "/api/admin/logs/"
        response = admin_client.get(url)
        assert response.status_code == 500
        assert "error" in response.data

    def test_admin_payout_action_invalid_state(self, admin_client, driver_user):
        payout = Payout.objects.create(
            driver=driver_user, amount=100, fee=10, net_amount=90, status=Payout.Status.PAID, reference="P_INV"
        )

        url = reverse('admin-payout-action', kwargs={'action': 'approve', 'payout_id': payout.id})
        response = admin_client.post(url)
        assert response.status_code == 400
        assert "Can only approve" in response.data["error"]

        url = reverse('admin-payout-action', kwargs={'action': 'reject', 'payout_id': payout.id})
        response = admin_client.post(url)
        assert response.status_code == 400
        assert "Can only reject" in response.data["error"]

    def test_admin_payout_action_invalid_action(self, admin_client, driver_user):
        payout = Payout.objects.create(
            driver=driver_user, amount=100, fee=10, net_amount=90, status=Payout.Status.REQUESTED, reference="P_INV2"
        )

        url = reverse('admin-payout-action', kwargs={'action': 'dance', 'payout_id': payout.id})
        response = admin_client.post(url)
        assert response.status_code == 400
        assert response.data["error"] == "Invalid action"

    def test_admin_fare_config_status_filters(self, admin_client):




        # Test status filters in various views to increase coverage
        url = "/api/admin/drivers/?status=ONLINE"
        response = admin_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        
        url = "/api/admin/payouts/?status=PENDING"
        response = admin_client.get(url)
        assert response.status_code == status.HTTP_200_OK

        url = "/api/admin/live-rides/?status=SEARCHING"
        response = admin_client.get(url)
        assert response.status_code == status.HTTP_200_OK
