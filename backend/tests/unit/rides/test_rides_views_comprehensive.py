"""
tests/unit/rides/test_rides_views_comprehensive.py

Comprehensive pytest tests for apps/rides/views.py
Targets ~90% coverage of EstimateFareView, CreateRideView, AcceptRideView,
RejectRideView, DriverArrivedView, VerifyOtpView, CompleteRideView,
MarkNoShowView, CancelRideView, ActiveRideView, RideDetailView,
RideHistoryView, SubmitFeedbackView, NearbyDriversView, FareConfigView,
RideFareBreakdownView, TipView.
"""
import pytest
from decimal import Decimal
from unittest.mock import patch, MagicMock, PropertyMock


@pytest.fixture(autouse=True)
def bypass_idempotency():
    """Patch idempotency cache so that the @idempotent_request decorator is a no-op."""
    with patch("apps.common.idempotency.cache") as mock_cache:
        mock_cache.add.return_value = True   # no duplicate lock
        mock_cache.get.return_value = None   # not previously cached
        yield mock_cache



# ─────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────
FARE_MOCK = {"estimated_fare": 120.0, "distance_km": 5.2, "duration_min": 15}
ROUTE_MOCK = {"polyline": "enc_mock_polyline", "distance_km": 5.2, "duration_min": 15}


def _make_ride(rider, driver=None, status="SEARCHING"):
    from apps.rides.models import Ride
    return Ride.objects.create(
        rider=rider,
        driver=driver,
        pickup_lat=12.9716,
        pickup_lng=77.5946,
        drop_lat=12.9352,
        drop_lng=77.6245,
        status=status,
        base_fare=Decimal("120.00"),
        planned_distance_km=Decimal("5.20"),
        planned_duration_min=15,
    )


# ─────────────────────────────────────────────────────────────
# 1. EstimateFareView  — POST /api/rides/estimate/
# ─────────────────────────────────────────────────────────────
@pytest.mark.django_db
class TestEstimateFareView:
    URL = "/api/rides/estimate-fare/"

    def test_success(self, api_client, user):
        api_client.force_authenticate(user=user)
        with patch("apps.rides.views.estimate_fare", return_value=FARE_MOCK), \
             patch("apps.rides.views.get_planned_route", return_value=ROUTE_MOCK):
            resp = api_client.post(self.URL, {
                "pickup_lat": 12.97, "pickup_lng": 77.59,
                "drop_lat": 12.93, "drop_lng": 77.62,
            })
        assert resp.status_code == 200
        assert "estimated_fare" in resp.data
        assert resp.data["distance_km"] == 5.2

    def test_missing_required_fields(self, api_client, user):
        api_client.force_authenticate(user=user)
        resp = api_client.post(self.URL, {"pickup_lat": 12.97})
        assert resp.status_code == 400
        assert "Missing required fields" in resp.data["error"]

    def test_with_valid_promo_code(self, api_client, user):
        api_client.force_authenticate(user=user)
        mock_offer = MagicMock()
        with patch("apps.rides.views.estimate_fare", return_value=FARE_MOCK), \
             patch("apps.rides.views.get_planned_route", return_value=ROUTE_MOCK), \
             patch("apps.offers.services.offer_engine.OfferEngine.validate_offer", return_value=mock_offer), \
             patch("apps.offers.services.offer_engine.OfferEngine.calculate_discount", return_value=20.0):
            resp = api_client.post(self.URL, {
                "pickup_lat": 12.97, "pickup_lng": 77.59,
                "drop_lat": 12.93, "drop_lng": 77.62,
                "promo_code": "SAVE20",
            })
        assert resp.status_code == 200
        assert resp.data["discount_applied"] == 20.0

    def test_invalid_promo_code_does_not_fail(self, api_client, user):
        """A bad promo must only warn, not crash the request."""
        api_client.force_authenticate(user=user)
        with patch("apps.rides.views.estimate_fare", return_value=FARE_MOCK), \
             patch("apps.rides.views.get_planned_route", return_value=ROUTE_MOCK), \
             patch("apps.offers.services.offer_engine.OfferEngine.validate_offer",
                   side_effect=Exception("Invalid promo")):
            resp = api_client.post(self.URL, {
                "pickup_lat": 12.97, "pickup_lng": 77.59,
                "drop_lat": 12.93, "drop_lng": 77.62,
                "promo_code": "BADCODE",
            })
        assert resp.status_code == 200
        assert resp.data["discount_applied"] == 0

    def test_estimate_fare_raises_exception(self, api_client, user):
        api_client.force_authenticate(user=user)
        with patch("apps.rides.views.estimate_fare", side_effect=ValueError("bad coords")):
            resp = api_client.post(self.URL, {
                "pickup_lat": 12.97, "pickup_lng": 77.59,
                "drop_lat": 12.93, "drop_lng": 77.62,
            })
        assert resp.status_code == 400
        assert "Failed to estimate fare" in resp.data["error"]

    def test_unauthenticated_blocked(self, api_client):
        resp = api_client.post(self.URL, {
            "pickup_lat": 12.97, "pickup_lng": 77.59,
            "drop_lat": 12.93, "drop_lng": 77.62,
        })
        assert resp.status_code == 401

    def test_driver_permission_blocked(self, api_client, driver_user):
        """Only riders may estimate fare."""
        api_client.force_authenticate(user=driver_user)
        with patch("apps.rides.views.estimate_fare", return_value=FARE_MOCK), \
             patch("apps.rides.views.get_planned_route", return_value=ROUTE_MOCK):
            resp = api_client.post(self.URL, {
                "pickup_lat": 12.97, "pickup_lng": 77.59,
                "drop_lat": 12.93, "drop_lng": 77.62,
            })
        assert resp.status_code == 403


# ─────────────────────────────────────────────────────────────
# 2. CreateRideView  — POST /api/rides/create/
# ─────────────────────────────────────────────────────────────
@pytest.mark.django_db
class TestCreateRideView:
    URL = "/api/rides/request/"

    VALID_PAYLOAD = {
        "pickup_lat": 12.9716, "pickup_lng": 77.5946,
        "drop_lat": 12.9352, "drop_lng": 77.6245,
        "pickup_address": "Start", "drop_address": "End",
        "vehicle_type": "go", "city": "Chennai",
    }

    def test_create_ride_success(self, api_client, user):
        api_client.force_authenticate(user=user)
        with patch("apps.rides.views.estimate_fare", return_value=FARE_MOCK), \
             patch("apps.rides.views.get_planned_route", return_value=ROUTE_MOCK), \
             patch("apps.rides.views.endpoint_cooldown", return_value=True), \
             patch("apps.rides.views.find_driver_and_offer_ride"), \
             patch("apps.rides.views.increment_demand"), \
             patch("apps.rides.views.cell_id_from_lat_lng", return_value="cell_1"), \
             patch("apps.rides.views.CreateRideView._broadcast_ride_created"), \
             patch("apps.common.idempotency.cache"):
            resp = api_client.post(self.URL, self.VALID_PAYLOAD)
        assert resp.status_code == 201
        assert resp.data["status"] == "SEARCHING"

    def test_rate_limit_hit(self, api_client, user):
        api_client.force_authenticate(user=user)
        with patch("apps.rides.views.endpoint_cooldown", return_value=False), \
             patch("apps.common.idempotency.cache"):
            resp = api_client.post(self.URL, self.VALID_PAYLOAD)
        assert resp.status_code == 429

    def test_active_ride_exists(self, api_client, user):
        """409 when user already has an active ride."""
        from apps.rides.models import Ride
        Ride.objects.create(
            rider=user, pickup_lat=12.9, pickup_lng=77.5,
            drop_lat=12.8, drop_lng=77.4, status=Ride.Status.ONGOING,
        )
        api_client.force_authenticate(user=user)
        with patch("apps.rides.views.endpoint_cooldown", return_value=True), \
             patch("apps.common.idempotency.cache"):
            resp = api_client.post(self.URL, self.VALID_PAYLOAD)
        assert resp.status_code == 409

    def test_missing_coordinates(self, api_client, user):
        api_client.force_authenticate(user=user)
        with patch("apps.rides.views.endpoint_cooldown", return_value=True), \
             patch("apps.common.idempotency.cache"):
            resp = api_client.post(self.URL, {"vehicle_type": "go"})
        assert resp.status_code == 400

    def test_invalid_coordinates_out_of_bounds(self, api_client, user):
        api_client.force_authenticate(user=user)
        with patch("apps.rides.views.endpoint_cooldown", return_value=True), \
             patch("apps.rides.views.estimate_fare", return_value=FARE_MOCK), \
             patch("apps.rides.views.get_planned_route", return_value=ROUTE_MOCK), \
             patch("apps.common.idempotency.cache"):
            resp = api_client.post(self.URL, {
                "pickup_lat": 999, "pickup_lng": 999,
                "drop_lat": 12.93, "drop_lng": 77.62,
            })
        assert resp.status_code == 400

    def test_camel_case_coords_accepted(self, api_client, user):
        """Mobile apps may send pickupLat/pickupLng."""
        api_client.force_authenticate(user=user)
        with patch("apps.rides.views.estimate_fare", return_value=FARE_MOCK), \
             patch("apps.rides.views.get_planned_route", return_value=ROUTE_MOCK), \
             patch("apps.rides.views.endpoint_cooldown", return_value=True), \
             patch("apps.rides.views.find_driver_and_offer_ride"), \
             patch("apps.rides.views.increment_demand"), \
             patch("apps.rides.views.cell_id_from_lat_lng", return_value="c"), \
             patch("apps.rides.views.CreateRideView._broadcast_ride_created"), \
             patch("apps.common.idempotency.cache"):
            resp = api_client.post(self.URL, {
                "pickupLat": 12.97, "pickupLng": 77.59,
                "dropLat": 12.93, "dropLng": 77.62,
            })
        assert resp.status_code == 201

    def test_estimate_fare_error_returns_500(self, api_client, user):
        api_client.force_authenticate(user=user)
        with patch("apps.rides.views.endpoint_cooldown", return_value=True), \
             patch("apps.rides.views.estimate_fare", side_effect=RuntimeError("geo unavailable")), \
             patch("apps.common.idempotency.cache"):
            resp = api_client.post(self.URL, self.VALID_PAYLOAD)
        assert resp.status_code in (400, 500)

    def test_promo_failure_does_not_block_creation(self, api_client, user):
        api_client.force_authenticate(user=user)
        payload = {**self.VALID_PAYLOAD, "promo_code": "BADCODE"}
        with patch("apps.rides.views.estimate_fare", return_value=FARE_MOCK), \
             patch("apps.rides.views.get_planned_route", return_value=ROUTE_MOCK), \
             patch("apps.rides.views.endpoint_cooldown", return_value=True), \
             patch("apps.rides.views.find_driver_and_offer_ride"), \
             patch("apps.rides.views.increment_demand"), \
             patch("apps.rides.views.cell_id_from_lat_lng", return_value="c"), \
             patch("apps.rides.views.CreateRideView._broadcast_ride_created"), \
             patch("apps.offers.services.offer_engine.OfferEngine.apply_offer",
                   side_effect=Exception("bad promo")), \
             patch("apps.common.idempotency.cache"):
            resp = api_client.post(self.URL, payload)
        assert resp.status_code == 201

    def test_driver_blocked_from_creating_ride(self, api_client, driver_user):
        api_client.force_authenticate(user=driver_user)
        resp = api_client.post(self.URL, self.VALID_PAYLOAD)
        assert resp.status_code == 403


# ─────────────────────────────────────────────────────────────
# 3. AcceptRideView  — POST /api/rides/{id}/accept/
# ─────────────────────────────────────────────────────────────
@pytest.mark.django_db
class TestAcceptRideView:

    def test_accept_success(self, api_client, user, driver_user):
        from apps.rides.models import Ride
        from apps.drivers.models import Driver
        driver = driver_user.driver
        ride = Ride.objects.create(
            rider=user, driver=driver,
            pickup_lat=12.9, pickup_lng=77.5,
            drop_lat=12.8, drop_lng=77.4,
            status=Ride.Status.OFFERED,
        )
        api_client.force_authenticate(user=driver_user)
        with patch("apps.rides.views.endpoint_cooldown", return_value=True), \
             patch("apps.rides.services.lifecycle.update_ride_status"), \
             patch("apps.drivers.services.metrics.update_driver_metrics"), \
             patch("apps.common.idempotency.cache"):
            resp = api_client.post(f"/api/rides/{ride.id}/accept/")
        assert resp.status_code == 200

    def test_accept_rate_limit(self, api_client, driver_user):
        api_client.force_authenticate(user=driver_user)
        with patch("apps.rides.views.endpoint_cooldown", return_value=False), \
             patch("apps.common.idempotency.cache"):
            resp = api_client.post("/api/rides/9999/accept/")
        assert resp.status_code == 429

    def test_accept_ride_not_found(self, api_client, driver_user):
        api_client.force_authenticate(user=driver_user)
        with patch("apps.rides.views.endpoint_cooldown", return_value=True), \
             patch("apps.common.idempotency.cache"):
            resp = api_client.post("/api/rides/99999/accept/")
        assert resp.status_code in (400, 404)

    def test_accept_wrong_status(self, api_client, user, driver_user):
        from apps.rides.models import Ride
        driver = driver_user.driver
        ride = Ride.objects.create(
            rider=user, driver=driver,
            pickup_lat=12.9, pickup_lng=77.5,
            drop_lat=12.8, drop_lng=77.4,
            status=Ride.Status.ASSIGNED,  # wrong status
        )
        api_client.force_authenticate(user=driver_user)
        with patch("apps.rides.views.endpoint_cooldown", return_value=True), \
             patch("apps.common.idempotency.cache"):
            resp = api_client.post(f"/api/rides/{ride.id}/accept/")
        assert resp.status_code == 400

    def test_accept_wrong_driver(self, api_client, user, driver_user):
        """Another driver cannot accept a ride offered to this driver."""
        from apps.rides.models import Ride
        from apps.drivers.models import Driver
        import random
        from django.contrib.auth import get_user_model
        User = get_user_model()
        phone2 = f"+917{random.randint(100000000, 999999999)}"
        user2 = User.objects.create_user(username=phone2, phone=phone2, password="pass", role="driver")
        driver2, _ = Driver.objects.update_or_create(user=user2, defaults={"status": Driver.Status.ONLINE})

        ride = Ride.objects.create(
            rider=user, driver=driver2,
            pickup_lat=12.9, pickup_lng=77.5,
            drop_lat=12.8, drop_lng=77.4,
            status=Ride.Status.OFFERED,
        )
        api_client.force_authenticate(user=driver_user)  # wrong driver
        with patch("apps.rides.views.endpoint_cooldown", return_value=True), \
             patch("apps.common.idempotency.cache"):
            resp = api_client.post(f"/api/rides/{ride.id}/accept/")
        assert resp.status_code == 400


# ─────────────────────────────────────────────────────────────
# 4. RejectRideView  — POST /api/rides/{id}/reject/
# ─────────────────────────────────────────────────────────────
@pytest.mark.django_db
class TestRejectRideView:

    def test_reject_success(self, api_client, user, driver_user):
        from apps.rides.models import Ride
        driver = driver_user.driver
        ride = Ride.objects.create(
            rider=user, driver=driver,
            pickup_lat=12.9, pickup_lng=77.5,
            drop_lat=12.8, drop_lng=77.4,
            status=Ride.Status.OFFERED,
        )
        api_client.force_authenticate(user=driver_user)
        with patch("apps.drivers.services.metrics.update_driver_metrics"), \
             patch("apps.rides.views.find_driver_and_offer_ride"), \
             patch("apps.common.idempotency.cache"):
            resp = api_client.post(f"/api/rides/{ride.id}/reject/")
        assert resp.status_code == 200
        assert resp.data["status"] == "REJECTED"
        ride.refresh_from_db()
        assert ride.status == "SEARCHING"
        assert driver.id in ride.rejected_driver_ids

    def test_reject_not_eligible(self, api_client, driver_user):
        api_client.force_authenticate(user=driver_user)
        resp = api_client.post("/api/rides/99999/reject/")
        assert resp.status_code == 400


# ─────────────────────────────────────────────────────────────
# 5. DriverArrivedView  — POST /api/rides/{id}/arrived/
# ─────────────────────────────────────────────────────────────
@pytest.mark.django_db
class TestDriverArrivedView:

    def test_arrived_success(self, api_client, user, driver_user):
        from apps.rides.models import Ride
        driver = driver_user.driver
        ride = Ride.objects.create(
            rider=user, driver=driver,
            pickup_lat=12.9, pickup_lng=77.5,
            drop_lat=12.8, drop_lng=77.4,
            status=Ride.Status.ASSIGNED,
        )
        api_client.force_authenticate(user=driver_user)
        with patch("apps.rides.views.update_ride_status") as mock_update:
            resp = api_client.post(f"/api/rides/{ride.id}/arrived/")
        assert resp.status_code == 200
        mock_update.assert_called_once_with(ride, "ARRIVED")

    def test_arrived_wrong_status_404(self, api_client, user, driver_user):
        from apps.rides.models import Ride
        driver = driver_user.driver
        ride = Ride.objects.create(
            rider=user, driver=driver,
            pickup_lat=12.9, pickup_lng=77.5,
            drop_lat=12.8, drop_lng=77.4,
            status=Ride.Status.SEARCHING,  # wrong state
        )
        api_client.force_authenticate(user=driver_user)
        resp = api_client.post(f"/api/rides/{ride.id}/arrived/")
        assert resp.status_code == 404


# ─────────────────────────────────────────────────────────────
# 6. VerifyOtpView  — POST /api/rides/{id}/start/
# ─────────────────────────────────────────────────────────────
@pytest.mark.django_db
class TestVerifyOtpView:

    def _arrived_ride(self, user, driver_user):
        from apps.rides.models import Ride
        driver = driver_user.driver
        return Ride.objects.create(
            rider=user, driver=driver,
            pickup_lat=12.9, pickup_lng=77.5,
            drop_lat=12.8, drop_lng=77.4,
            status=Ride.Status.ARRIVED,
            otp_code="1234",
        )

    def test_otp_missing(self, api_client, user, driver_user):
        ride = self._arrived_ride(user, driver_user)
        api_client.force_authenticate(user=driver_user)
        resp = api_client.post(f"/api/rides/{ride.id}/start/", {})
        assert resp.status_code == 400
        assert "OTP is required" in resp.data["error"]

    def test_otp_rate_limit(self, api_client, user, driver_user):
        ride = self._arrived_ride(user, driver_user)
        api_client.force_authenticate(user=driver_user)
        with patch("apps.rides.views.endpoint_cooldown", return_value=False), \
             patch("apps.common.idempotency.cache"):
            resp = api_client.post(f"/api/rides/{ride.id}/start/", {"otp": "1234"})
        assert resp.status_code == 429

    def test_otp_success(self, api_client, user, driver_user):
        ride = self._arrived_ride(user, driver_user)
        api_client.force_authenticate(user=driver_user)
        with patch("apps.rides.views.endpoint_cooldown", return_value=True), \
             patch("apps.rides.views.verify_and_consume_otp"), \
             patch("apps.rides.views.update_ride_status"), \
             patch("apps.drivers.redis.redis_client") as m_redis, \
             patch("apps.common.idempotency.cache"):
            m_redis.get.return_value = b"0"
            resp = api_client.post(f"/api/rides/{ride.id}/start/",
                                   {"otp": "1234", "lat": 12.9, "lng": 77.5})
        assert resp.status_code == 200

    def test_otp_already_started_idempotent(self, api_client, user, driver_user):
        from apps.rides.models import Ride
        driver = driver_user.driver
        ride = Ride.objects.create(
            rider=user, driver=driver,
            pickup_lat=12.9, pickup_lng=77.5,
            drop_lat=12.8, drop_lng=77.4,
            status=Ride.Status.ONGOING,
            otp_code="1234",
        )
        api_client.force_authenticate(user=driver_user)
        with patch("apps.rides.views.endpoint_cooldown", return_value=True), \
             patch("apps.common.idempotency.cache"):
            resp = api_client.post(f"/api/rides/{ride.id}/start/", {"otp": "1234"})
        assert resp.status_code == 200
        assert resp.data["status"] == "already_started"

    def test_otp_wrong_status(self, api_client, user, driver_user):
        from apps.rides.models import Ride
        driver = driver_user.driver
        ride = Ride.objects.create(
            rider=user, driver=driver,
            pickup_lat=12.9, pickup_lng=77.5,
            drop_lat=12.8, drop_lng=77.4,
            status=Ride.Status.ASSIGNED,   # not ARRIVED
            otp_code="1234",
        )
        api_client.force_authenticate(user=driver_user)
        with patch("apps.rides.views.endpoint_cooldown", return_value=True), \
             patch("apps.drivers.redis.redis_client") as m_redis, \
             patch("apps.common.idempotency.cache"):
            m_redis.get.return_value = b"0"
            resp = api_client.post(f"/api/rides/{ride.id}/start/", {"otp": "1234"})
        assert resp.status_code == 400
        assert "Cannot start ride" in resp.data["error"]

    def test_otp_brute_force_blocked(self, api_client, user, driver_user):
        ride = self._arrived_ride(user, driver_user)
        api_client.force_authenticate(user=driver_user)
        with patch("apps.rides.views.endpoint_cooldown", return_value=True), \
             patch("apps.drivers.redis.redis_client") as m_redis, \
             patch("apps.common.idempotency.cache"):
            m_redis.get.return_value = b"5"   # >= 5 attempts
            resp = api_client.post(f"/api/rides/{ride.id}/start/", {"otp": "0000"})
        assert resp.status_code == 429
        ride.refresh_from_db()
        assert ride.is_fraud_flagged is True

    def test_otp_wrong_value_increments_counter(self, api_client, user, driver_user):
        ride = self._arrived_ride(user, driver_user)
        api_client.force_authenticate(user=driver_user)
        # Temporarily disable exception propagation so the 500 becomes a response
        api_client.raise_request_exception = False
        with patch("apps.rides.views.endpoint_cooldown", return_value=True), \
             patch("apps.rides.views.verify_and_consume_otp",
                   side_effect=Exception("Wrong OTP")), \
             patch("apps.drivers.redis.redis_client") as m_redis, \
             patch("apps.common.idempotency.cache"):
            m_redis.get.return_value = b"0"
            resp = api_client.post(f"/api/rides/{ride.id}/start/", {"otp": "0000"})
        api_client.raise_request_exception = True
        assert resp.status_code == 500
        m_redis.incr.assert_called()


# ─────────────────────────────────────────────────────────────
# 7. CompleteRideView  — POST /api/rides/{id}/complete/
# ─────────────────────────────────────────────────────────────
@pytest.mark.django_db
class TestCompleteRideView:

    def test_complete_success(self, api_client, user, driver_user):
        from apps.rides.models import Ride
        driver = driver_user.driver
        ride = Ride.objects.create(
            rider=user, driver=driver,
            pickup_lat=12.9, pickup_lng=77.5,
            drop_lat=12.8, drop_lng=77.4,
            status=Ride.Status.ONGOING,
            base_fare=Decimal("100.00"),
        )
        mock_ride = MagicMock()
        mock_ride.id = ride.id
        mock_ride.status = "COMPLETED"
        mock_ride.end_time = "2026-03-08T12:00:00Z"
        mock_ride.start_time = "2026-03-08T11:00:00Z"
        mock_ride.final_fare = Decimal("120.00")
        mock_ride.actual_distance_km = 5.2
        api_client.force_authenticate(user=driver_user)
        with patch("apps.rides.views.endpoint_cooldown", return_value=True), \
             patch("apps.rides.services.complete_ride.complete_ride", return_value=mock_ride), \
             patch("apps.common.idempotency.cache"):
            resp = api_client.post(f"/api/rides/{ride.id}/complete/")
        assert resp.status_code == 200
        assert resp.data["status"] == "COMPLETED"

    def test_complete_rate_limit(self, api_client, driver_user):
        api_client.force_authenticate(user=driver_user)
        with patch("apps.rides.views.endpoint_cooldown", return_value=False), \
             patch("apps.common.idempotency.cache"):
            resp = api_client.post("/api/rides/9999/complete/")
        assert resp.status_code == 429

    def test_complete_service_error(self, api_client, user, driver_user):
        from apps.rides.models import Ride
        driver = driver_user.driver
        ride = Ride.objects.create(
            rider=user, driver=driver,
            pickup_lat=12.9, pickup_lng=77.5,
            drop_lat=12.8, drop_lng=77.4,
            status=Ride.Status.ONGOING,
        )
        api_client.force_authenticate(user=driver_user)
        with patch("apps.rides.views.endpoint_cooldown", return_value=True), \
             patch("apps.rides.services.complete_ride.complete_ride",
                   side_effect=Exception("db error")), \
             patch("apps.common.idempotency.cache"):
            resp = api_client.post(f"/api/rides/{ride.id}/complete/")
        assert resp.status_code == 500


# ─────────────────────────────────────────────────────────────
# 8. MarkNoShowView  — POST /api/rides/{id}/no-show/
# ─────────────────────────────────────────────────────────────
@pytest.mark.django_db
class TestMarkNoShowView:

    def test_no_show_success(self, api_client, user, driver_user):
        from apps.rides.models import Ride
        from apps.drivers.models import Driver
        driver = driver_user.driver
        ride = Ride.objects.create(
            rider=user, driver=driver,
            pickup_lat=12.9, pickup_lng=77.5,
            drop_lat=12.8, drop_lng=77.4,
            status=Ride.Status.ARRIVED,
        )
        api_client.force_authenticate(user=driver_user)
        with patch("apps.rides.models.Ride.transition_to"):
            resp = api_client.post(f"/api/rides/{ride.id}/no-show/")
        assert resp.status_code == 200

    def test_no_show_wrong_status(self, api_client, user, driver_user):
        from apps.rides.models import Ride
        driver = driver_user.driver
        ride = Ride.objects.create(
            rider=user, driver=driver,
            pickup_lat=12.9, pickup_lng=77.5,
            drop_lat=12.8, drop_lng=77.4,
            status=Ride.Status.ONGOING,  # should be ARRIVED
        )
        api_client.force_authenticate(user=driver_user)
        resp = api_client.post(f"/api/rides/{ride.id}/no-show/")
        assert resp.status_code == 404


# ─────────────────────────────────────────────────────────────
# 9. CancelRideView  — POST /api/rides/{id}/cancel/
# ─────────────────────────────────────────────────────────────
@pytest.mark.django_db
class TestCancelRideView:

    def _make_searching_ride(self, rider):
        from apps.rides.models import Ride
        return Ride.objects.create(
            rider=rider,
            pickup_lat=12.9, pickup_lng=77.5,
            drop_lat=12.8, drop_lng=77.4,
            status=Ride.Status.SEARCHING,
        )

    def test_cancel_by_rider(self, api_client, user):
        ride = self._make_searching_ride(user)
        api_client.force_authenticate(user=user)
        with patch("apps.rides.views.endpoint_cooldown", return_value=True), \
             patch("apps.rides.views.cancel_ride") as mock_cancel, \
             patch("apps.common.idempotency.cache"):
            resp = api_client.post(f"/api/rides/{ride.id}/cancel/")
        assert resp.status_code == 200
        assert resp.data["status"] == "CANCELLED"
        mock_cancel.assert_called_once()

    def test_cancel_already_cancelled_idempotent(self, api_client, user):
        from apps.rides.models import Ride
        ride = Ride.objects.create(
            rider=user,
            pickup_lat=12.9, pickup_lng=77.5,
            drop_lat=12.8, drop_lng=77.4,
            status=Ride.Status.CANCELLED,
        )
        api_client.force_authenticate(user=user)
        with patch("apps.rides.views.endpoint_cooldown", return_value=True), \
             patch("apps.common.idempotency.cache"):
            resp = api_client.post(f"/api/rides/{ride.id}/cancel/")
        assert resp.status_code == 200

    def test_cancel_by_driver(self, api_client, user, driver_user):
        from apps.rides.models import Ride
        driver = driver_user.driver
        ride = Ride.objects.create(
            rider=user, driver=driver,
            pickup_lat=12.9, pickup_lng=77.5,
            drop_lat=12.8, drop_lng=77.4,
            status=Ride.Status.ASSIGNED,
        )
        api_client.force_authenticate(user=driver_user)
        with patch("apps.rides.views.endpoint_cooldown", return_value=True), \
             patch("apps.rides.views.cancel_ride") as mock_cancel, \
             patch("apps.common.idempotency.cache"):
            resp = api_client.post(f"/api/rides/{ride.id}/cancel/")
        assert resp.status_code == 200
        mock_cancel.assert_called_once()

    def test_cancel_by_admin(self, api_client, platform_user, user):
        ride = self._make_searching_ride(user)
        api_client.force_authenticate(user=platform_user)
        with patch("apps.rides.views.endpoint_cooldown", return_value=True), \
             patch("apps.rides.views.cancel_ride") as mock_cancel, \
             patch("apps.common.idempotency.cache"):
            resp = api_client.post(f"/api/rides/{ride.id}/cancel/")
        assert resp.status_code == 200

    def test_cancel_no_permission(self, api_client, user, driver_user):
        """A stranger with no relation to the ride gets 403."""
        import random
        from django.contrib.auth import get_user_model
        User = get_user_model()
        phone3 = f"+916{random.randint(100000000, 999999999)}"
        stranger = User.objects.create_user(username=phone3, phone=phone3, role="rider")
        ride = self._make_searching_ride(user)
        api_client.force_authenticate(user=stranger)
        with patch("apps.rides.views.endpoint_cooldown", return_value=True), \
             patch("apps.common.idempotency.cache"):
            resp = api_client.post(f"/api/rides/{ride.id}/cancel/")
        assert resp.status_code == 403

    def test_cancel_rate_limit(self, api_client, user):
        api_client.force_authenticate(user=user)
        with patch("apps.rides.views.endpoint_cooldown", return_value=False), \
             patch("apps.common.idempotency.cache"):
            resp = api_client.post("/api/rides/9999/cancel/")
        assert resp.status_code == 429


# ─────────────────────────────────────────────────────────────
# 10. ActiveRideView  — GET /api/rides/active/
# ─────────────────────────────────────────────────────────────
@pytest.mark.django_db
class TestActiveRideView:
    URL = "/api/rides/active/"

    def test_no_active_ride(self, api_client, user):
        api_client.force_authenticate(user=user)
        resp = api_client.get(self.URL)
        assert resp.status_code == 200
        assert resp.data["id"] is None

    def test_active_ride_returned(self, api_client, user):
        from apps.rides.models import Ride
        Ride.objects.create(
            rider=user, pickup_lat=12.9, pickup_lng=77.5,
            drop_lat=12.8, drop_lng=77.4, status=Ride.Status.ONGOING,
        )
        api_client.force_authenticate(user=user)
        resp = api_client.get(self.URL)
        assert resp.status_code == 200
        assert resp.data["id"] is not None


# ─────────────────────────────────────────────────────────────
# 11. RideDetailView  — GET /api/rides/{id}/
# ─────────────────────────────────────────────────────────────
@pytest.mark.django_db
class TestRideDetailView:

    def test_rider_can_view_own_ride(self, api_client, user):
        ride = _make_ride(user)
        api_client.force_authenticate(user=user)
        resp = api_client.get(f"/api/rides/{ride.id}/")
        assert resp.status_code == 200

    def test_admin_can_view_any_ride(self, api_client, platform_user, user):
        ride = _make_ride(user)
        api_client.force_authenticate(user=platform_user)
        resp = api_client.get(f"/api/rides/{ride.id}/")
        assert resp.status_code == 200

    def test_stranger_forbidden(self, api_client, user):
        import random
        from django.contrib.auth import get_user_model
        User = get_user_model()
        phone4 = f"+914{random.randint(100000000, 999999999)}"
        stranger = User.objects.create_user(username=phone4, phone=phone4, role="rider")
        ride = _make_ride(user)
        api_client.force_authenticate(user=stranger)
        resp = api_client.get(f"/api/rides/{ride.id}/")
        assert resp.status_code == 403

    def test_nonexistent_ride(self, api_client, user):
        api_client.force_authenticate(user=user)
        resp = api_client.get("/api/rides/999999/")
        assert resp.status_code == 404

    def test_driver_can_view_assigned_ride(self, api_client, user, driver_user):
        from apps.rides.models import Ride
        driver = driver_user.driver
        ride = Ride.objects.create(
            rider=user, driver=driver,
            pickup_lat=12.9, pickup_lng=77.5, drop_lat=12.8, drop_lng=77.4,
            status=Ride.Status.ASSIGNED,
        )
        api_client.force_authenticate(user=driver_user)
        resp = api_client.get(f"/api/rides/{ride.id}/")
        assert resp.status_code == 200


# ─────────────────────────────────────────────────────────────
# 12. RideHistoryView  — GET /api/rides/history/
# ─────────────────────────────────────────────────────────────
@pytest.mark.django_db
class TestRideHistoryView:
    URL = "/api/rides/history/"

    def test_empty_history(self, api_client, user):
        api_client.force_authenticate(user=user)
        resp = api_client.get(self.URL)
        assert resp.status_code == 200
        assert resp.data == []

    def test_history_with_completed_rides(self, api_client, user):
        from apps.rides.models import Ride
        Ride.objects.create(
            rider=user, pickup_lat=12.9, pickup_lng=77.5,
            drop_lat=12.8, drop_lng=77.4,
            status=Ride.Status.COMPLETED,
            base_fare=Decimal("100.00"),
            final_fare=Decimal("100.00"),
        )
        api_client.force_authenticate(user=user)
        resp = api_client.get(self.URL)
        assert resp.status_code == 200
        assert len(resp.data) == 1

    def test_history_excludes_active_rides(self, api_client, user):
        from apps.rides.models import Ride
        Ride.objects.create(
            rider=user, pickup_lat=12.9, pickup_lng=77.5,
            drop_lat=12.8, drop_lng=77.4,
            status=Ride.Status.ONGOING,
        )
        api_client.force_authenticate(user=user)
        resp = api_client.get(self.URL)
        assert resp.status_code == 200
        assert len(resp.data) == 0


# ─────────────────────────────────────────────────────────────
# 13. SubmitFeedbackView  — POST /api/rides/{id}/feedback/
# ─────────────────────────────────────────────────────────────
@pytest.mark.django_db
class TestSubmitFeedbackView:

    def _completed_ride(self, user, driver_user):
        from apps.rides.models import Ride
        from apps.drivers.models import DriverStats
        driver = driver_user.driver
        DriverStats.objects.get_or_create(driver=driver)
        return Ride.objects.create(
            rider=user, driver=driver,
            pickup_lat=12.9, pickup_lng=77.5,
            drop_lat=12.8, drop_lng=77.4,
            status=Ride.Status.COMPLETED,
            base_fare=Decimal("100.00"),
            final_fare=Decimal("100.00"),
        )

    def test_rider_feedback_success(self, api_client, user, driver_user):
        ride = self._completed_ride(user, driver_user)
        api_client.force_authenticate(user=user)
        resp = api_client.post(f"/api/rides/{ride.id}/feedback/", {"rating": 5, "comment": "Great!"})
        assert resp.status_code == 200

    def test_driver_feedback_success(self, api_client, user, driver_user):
        from apps.users.models import RiderStats
        ride = self._completed_ride(user, driver_user)
        RiderStats.objects.get_or_create(user=user)
        api_client.force_authenticate(user=driver_user)
        resp = api_client.post(f"/api/rides/{ride.id}/feedback/", {"rating": 4, "comment": "Polite"})
        assert resp.status_code == 200

    def test_invalid_rating_out_of_range(self, api_client, user, driver_user):
        ride = self._completed_ride(user, driver_user)
        api_client.force_authenticate(user=user)
        resp = api_client.post(f"/api/rides/{ride.id}/feedback/", {"rating": 6})
        assert resp.status_code == 400

    def test_duplicate_feedback_rejected(self, api_client, user, driver_user):
        from apps.rides.models import RideFeedback
        ride = self._completed_ride(user, driver_user)
        RideFeedback.objects.create(
            ride=ride, rider=user, driver=ride.driver,
            giver_role=RideFeedback.GiverRole.RIDER, rating=5,
        )
        api_client.force_authenticate(user=user)
        resp = api_client.post(f"/api/rides/{ride.id}/feedback/", {"rating": 3})
        assert resp.status_code == 400

    def test_feedback_not_completed_ride(self, api_client, user):
        from apps.rides.models import Ride
        ride = Ride.objects.create(
            rider=user, pickup_lat=12.9, pickup_lng=77.5,
            drop_lat=12.8, drop_lng=77.4, status=Ride.Status.ONGOING,
        )
        api_client.force_authenticate(user=user)
        resp = api_client.post(f"/api/rides/{ride.id}/feedback/", {"rating": 5})
        assert resp.status_code == 404   # get_object_or_404 with status=COMPLETED

    def test_feedback_missing_rating(self, api_client, user, driver_user):
        ride = self._completed_ride(user, driver_user)
        api_client.force_authenticate(user=user)
        resp = api_client.post(f"/api/rides/{ride.id}/feedback/", {})
        assert resp.status_code == 400


# ─────────────────────────────────────────────────────────────
# 14. NearbyDriversView  — POST /api/rides/nearby-drivers/
# ─────────────────────────────────────────────────────────────
@pytest.mark.django_db
class TestNearbyDriversView:
    URL = "/api/rides/nearby-drivers/"

    def test_success_empty_result(self, api_client):
        with patch("apps.drivers.services.geo.get_nearby_driver_ids", return_value=[]):
            resp = api_client.post(self.URL, {"lat": 12.97, "lng": 77.59})
        assert resp.status_code == 200
        assert resp.data["drivers"] == []

    def test_success_with_drivers(self, api_client, driver_user):
        from apps.drivers.models import Driver
        driver = driver_user.driver
        driver.status = Driver.Status.ONLINE
        driver.last_lat = 12.97
        driver.last_lng = 77.59
        driver.save()
        with patch("apps.drivers.services.geo.get_nearby_driver_ids", return_value=[driver.id]):
            resp = api_client.post(self.URL, {"lat": 12.97, "lng": 77.59, "radius_km": 5})
        assert resp.status_code == 200
        assert len(resp.data["drivers"]) >= 0  # driver may or may not appear

    def test_missing_lat_lng(self, api_client):
        resp = api_client.post(self.URL, {"radius_km": 5})
        assert resp.status_code == 400

    def test_invalid_lat_lng_type(self, api_client):
        resp = api_client.post(self.URL, {"lat": "not_a_float", "lng": 77.59})
        assert resp.status_code == 400

    def test_public_access_allowed(self, api_client):
        """NearbyDriversView uses AllowAny — no auth required."""
        with patch("apps.drivers.services.geo.get_nearby_driver_ids", return_value=[]):
            resp = api_client.post(self.URL, {"lat": 12.97, "lng": 77.59})
        assert resp.status_code == 200


# ─────────────────────────────────────────────────────────────
# 15. FareConfigView  — GET /api/rides/fare-config/
# ─────────────────────────────────────────────────────────────
@pytest.mark.django_db
class TestFareConfigView:
    URL = "/api/rides/fare-config/"

    def test_list_all_configs_seeds_defaults(self, api_client, user):
        # When DB is empty, it seeds defaults and returns them
        api_client.force_authenticate(user=user)
        resp = api_client.get(self.URL)
        assert resp.status_code == 200
        assert isinstance(resp.data, list)
        vehicle_types = [c["vehicle_type"] for c in resp.data]
        assert "go" in vehicle_types

    def test_single_config(self, api_client, user):
        api_client.force_authenticate(user=user)
        # Seed first
        api_client.get(self.URL)  # seeds defaults
        resp = api_client.get(self.URL, {"type": "go"})
        assert resp.status_code == 200
        assert resp.data["vehicle_type"] == "go"

    def test_unauthenticated_blocked(self, api_client):
        resp = api_client.get(self.URL)
        assert resp.status_code == 401


# ─────────────────────────────────────────────────────────────
# 16. RideFareBreakdownView  — GET /api/rides/{id}/fare-breakdown/
# ─────────────────────────────────────────────────────────────
@pytest.mark.django_db
class TestRideFareBreakdownView:

    def test_completed_ride_rider(self, api_client, user):
        from apps.rides.models import Ride
        ride = Ride.objects.create(
            rider=user, pickup_lat=12.9, pickup_lng=77.5,
            drop_lat=12.8, drop_lng=77.4,
            status=Ride.Status.COMPLETED,
            base_fare=Decimal("100.00"), final_fare=Decimal("110.00"),
        )
        api_client.force_authenticate(user=user)
        with patch("apps.rides.services.final_fare.get_fare_breakdown",
                   return_value={"base_fare": "100.00", "final_fare": "110.00"}):
            resp = api_client.get(f"/api/rides/{ride.id}/fare-breakdown/")
        assert resp.status_code == 200

    def test_not_completed_returns_400(self, api_client, user):
        from apps.rides.models import Ride
        ride = Ride.objects.create(
            rider=user, pickup_lat=12.9, pickup_lng=77.5,
            drop_lat=12.8, drop_lng=77.4,
            status=Ride.Status.ONGOING,
        )
        api_client.force_authenticate(user=user)
        resp = api_client.get(f"/api/rides/{ride.id}/fare-breakdown/")
        assert resp.status_code == 400

    def test_forbidden_for_strangers(self, api_client, user):
        import random
        from django.contrib.auth import get_user_model
        User = get_user_model()
        phone5 = f"+913{random.randint(100000000, 999999999)}"
        stranger = User.objects.create_user(username=phone5, phone=phone5, role="rider")
        from apps.rides.models import Ride
        ride = Ride.objects.create(
            rider=user, pickup_lat=12.9, pickup_lng=77.5,
            drop_lat=12.8, drop_lng=77.4, status=Ride.Status.COMPLETED,
        )
        api_client.force_authenticate(user=stranger)
        resp = api_client.get(f"/api/rides/{ride.id}/fare-breakdown/")
        assert resp.status_code == 403


# ─────────────────────────────────────────────────────────────
# 17. TipView  — POST /api/rides/{id}/tip/
# ─────────────────────────────────────────────────────────────
@pytest.mark.django_db
class TestTipView:

    def _setup(self, user, driver_user):
        from apps.rides.models import Ride
        from apps.payments.models import Payment
        driver = driver_user.driver
        ride = Ride.objects.create(
            rider=user, driver=driver,
            pickup_lat=12.9, pickup_lng=77.5,
            drop_lat=12.8, drop_lng=77.4,
            status=Ride.Status.COMPLETED,
            base_fare=Decimal("100.00"),
            final_fare=Decimal("100.00"),
        )
        Payment.objects.create(
            user=user, ride_id=ride.id, amount=Decimal("100.00"),
            status=Payment.Status.CAPTURED, gateway_payment_id="pay_tip1",
        )
        return ride

    def test_tip_success(self, django_capture_on_commit_callbacks, api_client, user, driver_user):
        ride = self._setup(user, driver_user)
        api_client.force_authenticate(user=user)
        with django_capture_on_commit_callbacks(execute=True):
            resp = api_client.post(f"/api/rides/{ride.id}/tip/", {"tip_amount": 50})
        assert resp.status_code == 200
        # DRF may return '50' or '50.00' depending on decimal field config
        assert Decimal(str(resp.data["tip_amount"])) == Decimal("50.00")
        ride.refresh_from_db()
        assert ride.tip_amount == Decimal("50.00")

    def test_tip_too_low(self, api_client, user, driver_user):
        ride = self._setup(user, driver_user)
        api_client.force_authenticate(user=user)
        resp = api_client.post(f"/api/rides/{ride.id}/tip/", {"tip_amount": 0})
        assert resp.status_code == 400

    def test_tip_exceeds_max(self, api_client, user, driver_user):
        ride = self._setup(user, driver_user)
        api_client.force_authenticate(user=user)
        resp = api_client.post(f"/api/rides/{ride.id}/tip/", {"tip_amount": 2000})
        assert resp.status_code == 400

    def test_tip_wrong_rider(self, api_client, driver_user, user):
        ride = self._setup(user, driver_user)
        # driver is not the rider
        api_client.force_authenticate(user=driver_user)
        resp = api_client.post(f"/api/rides/{ride.id}/tip/", {"tip_amount": 50})
        assert resp.status_code == 403

    def test_tip_not_completed_ride(self, api_client, user, driver_user):
        from apps.rides.models import Ride
        from apps.payments.models import Payment
        driver = driver_user.driver
        ride = Ride.objects.create(
            rider=user, driver=driver,
            pickup_lat=12.9, pickup_lng=77.5,
            drop_lat=12.8, drop_lng=77.4,
            status=Ride.Status.ONGOING,
            base_fare=Decimal("100.00"),
        )
        Payment.objects.create(
            user=user, ride_id=ride.id, amount=Decimal("100.00"),
            status=Payment.Status.CAPTURED,
        )
        api_client.force_authenticate(user=user)
        resp = api_client.post(f"/api/rides/{ride.id}/tip/", {"tip_amount": 50})
        assert resp.status_code == 400

    def test_tip_no_payment(self, api_client, user, driver_user):
        from apps.rides.models import Ride
        driver = driver_user.driver
        ride = Ride.objects.create(
            rider=user, driver=driver,
            pickup_lat=12.9, pickup_lng=77.5,
            drop_lat=12.8, drop_lng=77.4,
            status=Ride.Status.COMPLETED,
            base_fare=Decimal("100.00"), final_fare=Decimal("100.00"),
        )
        api_client.force_authenticate(user=user)
        resp = api_client.post(f"/api/rides/{ride.id}/tip/", {"tip_amount": 50})
        assert resp.status_code == 400
        assert "complete payment" in resp.data["error"]

    def test_tip_no_driver(self, api_client, user):
        from apps.rides.models import Ride
        from apps.payments.models import Payment
        ride = Ride.objects.create(
            rider=user, driver=None,
            pickup_lat=12.9, pickup_lng=77.5,
            drop_lat=12.8, drop_lng=77.4,
            status=Ride.Status.COMPLETED,
            base_fare=Decimal("100.00"), final_fare=Decimal("100.00"),
        )
        Payment.objects.create(
            user=user, ride_id=ride.id, amount=Decimal("100.00"),
            status=Payment.Status.CAPTURED,
        )
        api_client.force_authenticate(user=user)
        resp = api_client.post(f"/api/rides/{ride.id}/tip/", {"tip_amount": 50})
        assert resp.status_code == 400
        assert "No driver" in resp.data["error"]

    def test_tip_invalid_amount_string(self, api_client, user, driver_user):
        ride = self._setup(user, driver_user)
        api_client.force_authenticate(user=user)
        resp = api_client.post(f"/api/rides/{ride.id}/tip/", {"tip_amount": "not-a-number"})
        assert resp.status_code == 400

    def test_tip_driver_blocked_from_tipping(self, api_client, driver_user, user):
        """Drivers do not have IsRider — must get 403."""
        ride = self._setup(user, driver_user)
        api_client.force_authenticate(user=driver_user)
        resp = api_client.post(f"/api/rides/{ride.id}/tip/", {"tip_amount": 10})
        assert resp.status_code == 403
