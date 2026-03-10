import pytest
import asyncio
import json
from unittest.mock import patch, MagicMock, AsyncMock
from decimal import Decimal
from django.urls import reverse
from django.utils import timezone
from django.core.files.uploadedfile import SimpleUploadedFile
from apps.users.models import User
from apps.rides.models import Ride
from apps.payments.models import LedgerEntry, Payout, Payment
from apps.supports.models import SupportTicket, Emergency
from apps.drivers.models import Driver, DriverStats, DriverDocument
from apps.common.idempotency import idempotent_request

# Force imports for coverage check
import apps.payments.admin_views
import apps.payments.views_wallet
import apps.payments.views_web
import apps.supports.views
import apps.drivers.views
import apps.notifications.services.alerts
import apps.admin_dashboard.views_admin
import apps.admin_dashboard.views
import apps.rides.admin_views
import apps.drivers.admin_views

@pytest.fixture
def admin_user(db):
    user = User.objects.create_superuser(username="adm_qg", email="a@qg.com", password="pass", phone="9988776655")
    user.role = User.ROLE_ADMIN
    user.is_verified = True
    user.save()
    return user

@pytest.fixture
def rider(db):
    return User.objects.create_user(username="rider_qg", phone="1122334455", password="pass", role=User.ROLE_RIDER)

@pytest.fixture
def driver_user(db):
    user = User.objects.create_user(username="dr_qg", phone="2233445566", password="pass", role=User.ROLE_DRIVER, first_name="Dr", last_name="Who")
    driver, _ = Driver.objects.get_or_create(user=user)
    driver.is_verified = True
    driver.save()
    DriverStats.objects.get_or_create(driver=driver)
    return user

@pytest.fixture
def ride(db, rider, driver_user):
    return Ride.objects.create(
        rider=rider, driver=driver_user.driver,
        pickup_lat=12.9, pickup_lng=77.5, drop_lat=13.0, drop_lng=77.6,
        status=Ride.Status.COMPLETED, final_fare=Decimal("100.00"),
        pickup_address="A", drop_address="B", vehicle_type="go",
        planned_route_polyline="abc"
    )

@pytest.fixture
def api_client():
    from rest_framework.test import APIClient
    return APIClient()

# ─── 1. ADMIN DASHBOARD & FINANCIALS ──────────────────────────────────────────
@pytest.mark.django_db
class TestAdminDashboardFull:
    def test_admin_views_comprehensive(self, api_client, admin_user, rider, driver_user, ride):
        api_client.force_authenticate(user=admin_user)
        
        # Admin Dashboard Views
        assert api_client.get("/api/admin/overview/").status_code == 200
        assert api_client.get("/api/admin/analytics/").status_code == 200
        assert api_client.get("/api/admin/live-map/snapshot/").status_code == 200
        assert api_client.get("/api/admin/live-rides/").status_code == 200
        assert api_client.get("/api/admin/alerts/").status_code == 200
        
        # Driver Management (Base)
        assert api_client.get("/api/admin/drivers/").status_code == 200
        assert api_client.post(f"/api/admin/drivers/{driver_user.driver.id}/action/", {"action": "BLOCK"}).status_code == 200
        
        # Admin Ledger & Payouts
        assert api_client.get("/api/admin/payments/").status_code == 200
        payout = Payout.objects.create(driver=driver_user, amount=100, fee=0, net_amount=100, reference="p1")
        assert api_client.post(f"/api/admin/payout/resolve/{payout.id}/").status_code == 200
        
        # Support Tickets Overview
        assert api_client.get("/api/admin/tickets/").status_code == 200
        assert api_client.post("/api/admin/resolve-ride/", {"ride_id": ride.id, "action": "CANCEL"}).status_code == 200

# ─── 2. PAYMENTS WALLET & WEB ────────────────────────────────────────────────
@pytest.mark.django_db
class TestPaymentsWalletExtended:
    def test_wallet_views(self, api_client, rider):
        api_client.force_authenticate(user=rider)
        assert api_client.get("/api/payments/wallet/").status_code == 200
        assert api_client.get("/api/payments/transactions/").status_code == 200

    @patch("apps.payments.views_web.razorpay_client")
    def test_web_checkout_and_verify(self, mock_razor, api_client, rider, ride):
        api_client.force_authenticate(user=rider)
        mock_razor.auth = ("key", "secret")
        mock_razor.order.create.return_value = {"id": "ord_spec_7"}
        
        assert api_client.get(f"/api/payments/checkout/{ride.id}/").status_code == 200
        
        mock_razor.utility.verify_payment_signature.return_value = True
        Payment.objects.get_or_create(user=rider, ride_id=ride.id, gateway_order_id="ord_spec_7", defaults={"amount": 100})
        
        data = {"razorpay_order_id": "ord_spec_7", "razorpay_payment_id": "pay_7", "razorpay_signature": "sig_7"}
        with patch("apps.payments.services.payout.settle_driver_payout"):
            resp = api_client.post("/api/payments/verify-web/", data)
            assert resp.status_code == 302

    def test_web_verify_failure_paths(self, api_client, rider, ride):
        api_client.force_authenticate(user=rider)
        with patch("apps.payments.views_web.razorpay_client") as mock_razor:
            mock_razor.utility.verify_payment_signature.side_effect = Exception("Invalid Sig")
            data = {"razorpay_order_id": "err_1", "razorpay_payment_id": "p1", "razorpay_signature": "s1"}
            resp = api_client.post("/api/payments/verify-web/", data)
            assert resp.status_code == 302

# ─── 3. SUPPORTS & EMERGENCY ─────────────────────────────────────────────────
@pytest.mark.django_db
class TestSupportsExtended:
    def test_emergency_flow(self, api_client, rider, ride, admin_user):
        api_client.force_authenticate(user=rider)
        with patch("channels.layers.get_channel_layer") as mock_get_layer:
            mock_layer = MagicMock()
            mock_layer.group_send = AsyncMock()
            mock_get_layer.return_value = mock_layer
            
            resp = api_client.post(f"/api/supports/rides/{ride.id}/sos/", {"lat": 12.0, "lng": 77.0})
            assert resp.status_code == 200
            eid = resp.data["emergency_id"]
            
        api_client.force_authenticate(user=admin_user)
        with patch("channels.layers.get_channel_layer") as mock_get_layer:
            mock_layer = MagicMock()
            mock_layer.group_send = AsyncMock()
            mock_get_layer.return_value = mock_layer
            assert api_client.post(f"/api/supports/emergencies/{eid}/resolve/", {"status": "RESOLVED"}).status_code == 200

    def test_ticket_resolve_refund(self, api_client, admin_user, rider, ride):
        ticket = SupportTicket.objects.create(user=rider, ride=ride, reason="refund")
        api_client.force_authenticate(user=admin_user)
        with patch("apps.supports.views.resolve_with_refund") as mock_r:
            assert api_client.post(f"/api/supports/tickets/{ticket.id}/resolve/", {"refund_amount": 50}).status_code == 200
            mock_r.assert_called_once()

# ─── 4. DRIVERS ACTIONS & LOCATION ──────────────────────────────────────────
@pytest.mark.django_db
class TestDriversViewsExtended:
    def test_onboarding_and_upload(self, api_client, driver_user):
        api_client.force_authenticate(user=driver_user)
        assert api_client.get("/api/drivers/me/").status_code == 200
        
        file = SimpleUploadedFile("license.jpg", b"content", content_type="image/jpeg")
        resp = api_client.post("/api/drivers/documents/upload/", {"document_type": "LICENSE", "file": file}, format="multipart")
        assert resp.status_code == 200

    def test_location_and_status_logic(self, api_client, driver_user, ride):
        api_client.force_authenticate(user=driver_user)
        
        with patch("channels.layers.get_channel_layer") as mock_get_layer, \
             patch("apps.drivers.redis.update_driver_location"), \
             patch("apps.rides.services.deviation.check_route_deviation", return_value=(True, 500)):
            
            mock_layer = MagicMock()
            mock_layer.group_send = AsyncMock()
            mock_get_layer.return_value = mock_layer
            
            ride.status = Ride.Status.ONGOING
            ride.save()
            
            resp = api_client.post("/api/drivers/location/", {"lat": 12.95, "lng": 77.55})
            assert resp.status_code == 200

        ride.status = Ride.Status.COMPLETED
        ride.save()
        with patch("channels.layers.get_channel_layer") as mock_get:
            mock_layer = MagicMock()
            mock_layer.group_send = AsyncMock()
            mock_get.return_value = mock_layer
            with patch("apps.drivers.services.geo.add_driver_to_geo"), \
                 patch("apps.drivers.services.geo.remove_driver_from_geo"):
                assert api_client.post("/api/drivers/status/", {"status": "ONLINE"}).status_code == 200
                assert api_client.post("/api/drivers/status/", {"status": "OFFLINE"}).status_code == 200

# ─── 5. UTILITIES (IDEMPOTENCY & ALERTS) ────────────────────────────────────
@pytest.mark.django_db
class TestUtilitiesExtended:
    def test_idempotent_decorator(self, rider):
        class MockView:
            @idempotent_request(ttl=3600)
            def post(self, request):
                from rest_framework.response import Response
                return Response({"result": "success"})

        view_inst = MockView()
        request = MagicMock()
        request.method = 'POST'
        request.user = rider
        request.headers = {'X-Idempotency-Key': 'unique_key_104'}
        
        with patch("apps.common.idempotency.cache.add", return_value=True), \
             patch("apps.common.idempotency.cache.set"):
            response = view_inst.post(request)
            assert response.status_code == 200

        cached_data = {'status': 200, 'data': {"result": "success"}}
        with patch("apps.common.idempotency.cache.add", return_value=False), \
             patch("apps.common.idempotency.cache.get", return_value=cached_data):
            response = view_inst.post(request)
            assert json.loads(response.content) == {"result": "success"}

    def test_alerts_service_levels(self):
        from apps.notifications.services.alerts import send_critical_alert
        from django.test import override_settings
        with patch("apps.notifications.services.alerts.get_channel_layer") as mock_get, \
             patch("asyncio.get_running_loop", side_effect=RuntimeError), \
             patch("requests.post") as mock_post:
            
            mock_layer = MagicMock()
            mock_layer.group_send = MagicMock()
            mock_get.return_value = mock_layer
            
            send_critical_alert("TITLE", "MSG", "CRITICAL")
            send_critical_alert("TITLE", "MSG", "WARNING")
            send_critical_alert("TITLE", "MSG", "INFO")
            
            with override_settings(SLACK_ALERTS_WEBHOOK_URL="http://slack.com"):
                with patch("django.core.cache.cache.get", return_value=None):
                    send_critical_alert("NEW_TITLE", "MSG", "ERROR")
                    assert mock_post.called

# ─── 6. ADMIN VIEWS (RIDES & DRIVERS) ───────────────────────────────────────
@pytest.mark.django_db
class TestAdminViewsExtended:
    def test_ride_admin_views(self, api_client, admin_user, ride):
        api_client.force_authenticate(user=admin_user)
        assert api_client.get("/api/rides/admin/rides/").status_code == 200
        assert api_client.get(f"/api/rides/{ride.id}/").status_code == 200
        
    def test_driver_admin_views(self, api_client, admin_user, driver_user):
        api_client.force_authenticate(user=admin_user)
        assert api_client.get("/api/drivers/admin/drivers/").status_code == 200
        assert api_client.get(f"/api/drivers/admin/drivers/{driver_user.driver.id}/").status_code == 200
        
        # Approve Document (Fix body)
        doc = DriverDocument.objects.create(driver=driver_user.driver, document_type="LICENSE", status="PENDING")
        assert api_client.post(f"/api/drivers/admin/documents/{doc.id}/approve/", {"action": "approve"}).status_code == 200

# ─── 7. PAYMENTS ADMIN (EXTRA) ───────────────────────────────────────────────
@pytest.mark.django_db
class TestPaymentsAdminExtra:
    def test_admin_ledger_check_validation(self, api_client, admin_user, rider):
        api_client.force_authenticate(user=admin_user)
        from apps.payments.admin_views import AdminLedgerCheckView
        from rest_framework.test import APIRequestFactory, force_authenticate
        factory = APIRequestFactory()
        view = AdminLedgerCheckView.as_view()
        
        req = factory.post("/fake/", {"user_id": rider.id}, format="json")
        force_authenticate(req, user=admin_user)
        with patch("apps.payments.admin_views.assert_user_ledger"):
             assert view(req).status_code == 200
        
        req = factory.post("/fake/", {}, format="json")
        force_authenticate(req, user=admin_user)
        assert view(req).status_code == 400
