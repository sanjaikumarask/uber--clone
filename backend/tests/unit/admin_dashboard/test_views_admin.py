import pytest
import json
from unittest.mock import patch
from django.urls import reverse
from rest_framework import status
from django.utils.timezone import now
from datetime import timedelta

from apps.users.models import User
from apps.payments.models import Payout, LedgerEntry, Payment
from apps.supports.models import SupportTicket, Emergency
from apps.rides.models import Ride
from apps.rides.fare_models import FareConfig
from apps.admin_dashboard.models import SystemLog
from apps.drivers.models import Driver

@pytest.mark.django_db
class TestAdminDashboardViews:
    @pytest.fixture
    def admin_user(self):
        user = User.objects.create_superuser(
            username="admin_view_test", 
            phone="+919000000001", 
            password="adminpassword",
            role=User.ROLE_ADMIN
        )
        return user

    @pytest.fixture
    def admin_client(self, api_client, admin_user):
        api_client.force_authenticate(user=admin_user)
        return api_client

    def test_admin_ledger_list(self, admin_client):
        user = User.objects.create_user(username="u1", phone="+91700")
        LedgerEntry.objects.create(
            user=user, 
            amount=100, 
            entry_type="CREDIT", 
            reason="REFUND",
            reference="TXN_LEDGER_1"
        )
        
        url = reverse('admin-ledger')
        response = admin_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 1

    def test_admin_payout_list(self, admin_client):
        driver_user = User.objects.create_user(username="d_payout", phone="+91800", role="driver")
        Payout.objects.create(
            driver=driver_user, 
            amount=500, 
            fee=10, 
            net_amount=490, 
            status="REQUESTED",
            reference="PAY_REF_100"
        )
        
        url = reverse('admin-payouts')
        response = admin_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 1

    @patch('apps.admin_dashboard.views_admin.execute_driver_payout')
    def test_admin_payout_approve(self, mock_execute_payout, admin_client):
        driver_user = User.objects.create_user(username="d_approve", phone="+91801", role="driver")
        payout = Payout.objects.create(
            driver=driver_user, 
            amount=500, 
            fee=10, 
            net_amount=490, 
            status="REQUESTED",
            reference="PAY_REF_200"
        )
        
        url = reverse('admin-payout-action', kwargs={'action': 'approve', 'payout_id': payout.id})
        response = admin_client.post(url)
        assert response.status_code == status.HTTP_200_OK
        payout.refresh_from_db()
        assert payout.status == "PROCESSING"
        mock_execute_payout.delay.assert_called_once_with(payout_id=payout.id)

    def test_admin_payout_reject(self, admin_client):
        driver_user = User.objects.create_user(username="d_reject", phone="+91802", role="driver")
        payout = Payout.objects.create(
            driver=driver_user, 
            amount=500, 
            fee=10, 
            net_amount=490, 
            status="REQUESTED",
            reference="PAY_REF_300"
        )
        
        url = reverse('admin-payout-action', kwargs={'action': 'reject', 'payout_id': payout.id})
        response = admin_client.post(url)
        assert response.status_code == status.HTTP_200_OK
        payout.refresh_from_db()
        assert payout.status == "FAILED"

    def test_admin_payout_resolve(self, admin_client):
        driver_user = User.objects.create_user(username="d_resolve_p", phone="+91803", role="driver")
        payout = Payout.objects.create(
            driver=driver_user, 
            amount=500, 
            fee=10, 
            net_amount=490, 
            status="REQUESTED",
            reference="PAY_REF_400"
        )
        
        url = reverse('admin-payout-action', kwargs={'action': 'resolve', 'payout_id': payout.id})
        response = admin_client.post(url)
        assert response.status_code == status.HTTP_200_OK
        payout.refresh_from_db()
        assert payout.status == "PAID"

    def test_admin_tickets_list(self, admin_client):
        user = User.objects.create_user(username="u_ticket", phone="+91701")
        ride = Ride.objects.create(
            rider=user, 
            pickup_lat=12.0, pickup_lng=77.0, 
            drop_lat=12.1, drop_lng=77.1,
            pickup_address="A", drop_address="B", 
            base_fare=100
        )
        SupportTicket.objects.create(
            ride=ride, 
            user=user, 
            reason="OTHER", 
            description="Bad", 
            status="OPEN"
        )
        Emergency.objects.create(
            ride=ride, 
            user=user, 
            lat=12.0, 
            lng=77.0, 
            status="ACTIVE"
        )
        
        url = reverse('admin-tickets')
        response = admin_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert 'tickets' in response.data
        assert 'emergencies' in response.data

    def test_admin_fare_config_list(self, admin_client):
        FareConfig.objects.get_or_create(vehicle_type="moto", defaults={"base_fare": 40})
        url = "/api/admin/fare-config/"
        response = admin_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 1

    def test_admin_fare_config_patch(self, admin_client):
        config, _ = FareConfig.objects.get_or_create(vehicle_type="xl", defaults={"base_fare": 100})
        url = f"/api/admin/fare-config/{config.id}/"
        response = admin_client.patch(url, {"base_fare": "120.00"})
        assert response.status_code == status.HTTP_200_OK
        config.refresh_from_db()
        assert float(config.base_fare) == 120.0

    def test_admin_live_rides(self, admin_client):
        user = User.objects.create_user(username="u_live_rides", phone="+91705")
        Ride.objects.create(
            rider=user, status=Ride.Status.ONGOING,
            pickup_lat=12.0, pickup_lng=77.0, 
            drop_lat=12.1, drop_lng=77.1,
            base_fare=100
        )
        url = "/api/admin/live-rides/"
        response = admin_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] >= 1

    def test_admin_payment_status(self, admin_client):
        user = User.objects.create_user(username="u_pay_status", phone="+91706")
        Payment.objects.create(user=user, amount=100, status=Payment.Status.CAPTURED, ride_id=999)
        
        url = "/api/admin/payments/status/"
        response = admin_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['summary']['success'] >= 1

    def test_admin_analytics(self, admin_client):
        user = User.objects.create_user(username="u_analytics", phone="+91707")
        Ride.objects.create(
            rider=user, status=Ride.Status.COMPLETED,
            pickup_lat=12.0, pickup_lng=77.0, 
            drop_lat=12.1, drop_lng=77.1,
            base_fare=100, final_fare=150
        )
        url = "/api/admin/analytics/"
        response = admin_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['lifetime']['total_revenue'] >= 150

    def test_admin_alerts(self, admin_client):
        SystemLog.objects.create(type=SystemLog.LogType.ERROR, message="Test Error Alert")
        url = "/api/admin/alerts/"
        response = admin_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 1

    def test_admin_driver_list(self, admin_client):
        user = User.objects.create_user(username="d_list_view", phone="+91805", role="driver")
        # Driver is automatically created by signals if everything is correct, 
        # but let's be explicit and handle possible IntegrityError
        Driver.objects.get_or_create(user=user, defaults={"status": Driver.Status.ONLINE})
        
        url = "/api/admin/drivers/"
        response = admin_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 1

    def test_admin_driver_action(self, admin_client):
        user = User.objects.create_user(username="d_action_view", phone="+91806", role="driver")
        driver, _ = Driver.objects.get_or_create(user=user, defaults={"status": Driver.Status.ONLINE, "is_verified": False})
        
        url = f"/api/admin/drivers/{driver.id}/action/"
        response = admin_client.post(url, {"action": "approve"})
        assert response.status_code == status.HTTP_200_OK
        driver.refresh_from_db()
        assert driver.is_verified is True

    def test_admin_live_map_snapshot(self, admin_client):
        user = User.objects.create_user(username="d_map_snap", phone="+91807", role="driver")
        driver, _ = Driver.objects.get_or_create(user=user)
        driver.status = Driver.Status.ONLINE
        driver.last_lat = 12.0
        driver.last_lng = 77.0
        driver.save()
        
        url = "/api/admin/live-map/snapshot/"
        response = admin_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['drivers']) >= 1


    @patch('redis.Redis.from_url')
    def test_admin_system_logs_view(self, mock_redis_url, admin_client):
        mock_redis = mock_redis_url.return_value
        mock_redis.lrange.return_value = [json.dumps({"level": "INFO", "message": "Log 1"})]
        
        url = "/api/admin/logs/"
        response = admin_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1

    def test_admin_resolve_ride_cancel(self, admin_client):
        user = User.objects.create_user(username="u_resolve_cancel", phone="+91703")
        ride = Ride.objects.create(
            rider=user, status=Ride.Status.SEARCHING,
            pickup_lat=12.0, pickup_lng=77.0, 
            drop_lat=12.1, drop_lng=77.1,
            pickup_address="A", drop_address="B",
            base_fare=100
        )
        url = "/api/admin/resolve-ride/"
        response = admin_client.post(url, {"ride_id": ride.id, "action": "CANCEL"})
        assert response.status_code == status.HTTP_200_OK
        ride.refresh_from_db()
        assert ride.status == Ride.Status.CANCELLED

    def test_admin_overview(self, admin_client):
        url = "/api/admin/overview/"
        response = admin_client.get(url)
        assert response.status_code == status.HTTP_200_OK
