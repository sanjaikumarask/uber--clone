import uuid
from unittest.mock import patch

import pytest
from django.utils import timezone
from rest_framework import status

from apps.drivers.models import Driver
from apps.rides.models import Ride
from apps.users.models import User


@pytest.mark.django_db
class TestRidesApiHighValue:
    """
    Principal Engineer's Resilience Suite for Ride API.
    Increases apps/rides/views.py (~48%) and apps/rides/tasks.py (~21%) coverage.
    """

    def setup_method(self):
        self.rider = User.objects.create_user(
            username=f"rider_{uuid.uuid4().hex[:4]}", role="rider"
        )
        self.driver_user = User.objects.create_user(
            username=f"driver_{uuid.uuid4().hex[:4]}", role="driver"
        )
        self.driver = self.driver_user.driver
        self.driver.status = Driver.Status.ONLINE
        self.driver.save()

    # --- 1. Ride Creation & Fare Estimatation (apps/rides/views.py coverage) ---

    def test_estimate_fare_invalid_states(self):
        """
        WHY: Validates input sanitization for GPS data.
        """
        from rest_framework.test import APIRequestFactory, force_authenticate

        from apps.rides.views import EstimateFareView

        factory = APIRequestFactory()
        request = factory.post(
            "/api/v1/rides/estimate/",
            {
                "pickup_lat": "invalid",
                "pickup_lng": 77.5946,
                "drop_lat": 12.9716,
                "drop_lng": 77.6000,
            },
            format="json",
        )
        force_authenticate(request, user=self.rider)

        view = EstimateFareView.as_view()
        response = view(request)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    # --- 2. Ride Lifecycle Exceptions (Accept/Reject/Arrive) ---

    def test_accept_ride_not_offered(self):
        """
        WHY: Prevents state hijacking. Only rides in OFFERED status can be accepted.
        """
        ride = Ride.objects.create(
            rider=self.rider,
            driver=self.driver,
            pickup_lat=12.9716,
            pickup_lng=77.5946,
            drop_lat=12.9352,
            drop_lng=77.6245,
            status=Ride.Status.ARRIVED,
            otp_code="1234",
        )

        from rest_framework.test import APIRequestFactory, force_authenticate

        from apps.rides.views import AcceptRideView

        factory = APIRequestFactory()
        request = factory.post(f"/api/v1/rides/{ride.id}/accept/")
        force_authenticate(request, user=self.driver_user)

        view = AcceptRideView.as_view()
        response = view(request, ride_id=ride.id)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "expected OFFERED" in str(response.data["error"])

    def test_driver_arrived_but_not_assigned(self):
        """
        WHY: Status Consistency. A driver cannot arrive if the ride isn't ASSIGNED to them.
        """
        other_user = User.objects.create_user(username="other_driver", role="driver")
        ride = Ride.objects.create(
            rider=self.rider,
            driver=other_user.driver,
            status=Ride.Status.ASSIGNED,
            pickup_lat=0,
            pickup_lng=0,
            drop_lat=0,
            drop_lng=0,
        )

        from rest_framework.test import APIRequestFactory, force_authenticate

        from apps.rides.views import DriverArrivedView

        factory = APIRequestFactory()
        request = factory.post(f"/api/v1/rides/{ride.id}/arrived/")
        force_authenticate(
            request, user=self.driver_user
        )  # CURRENT driver is NOT assigned

        view = DriverArrivedView.as_view()
        response = view(request, ride_id=ride.id)
        assert (
            response.status_code == status.HTTP_404_NOT_FOUND
        )  # get_object_or_404(driver__user=request.user)

    # --- 3. Ride Completion & OTP (apps/rides/views.py coverage) ---

    def test_verify_otp_invalid_driver_permissions(self):
        """
        WHY: Security: Ensures ONLY the assigned driver can verify the OTP.
        """
        other_user = User.objects.create_user(username="another_driver", role="driver")
        ride = Ride.objects.create(
            rider=self.rider,
            driver=self.driver,
            status=Ride.Status.ARRIVED,
            otp_code="1234",
            pickup_lat=0,
            pickup_lng=0,
            drop_lat=0,
            drop_lng=0,
        )

        from rest_framework.test import APIRequestFactory, force_authenticate

        from apps.rides.views import VerifyOtpView

        factory = APIRequestFactory()
        request = factory.post(
            f"/api/v1/rides/{ride.id}/verify-otp/", {"otp": "1234"}, format="json"
        )
        force_authenticate(request, user=other_user)  # Wrong driver

        view = VerifyOtpView.as_view()
        response = view(request, ride_id=ride.id)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    # --- 4. Rides Maintenance Tasks (apps/rides/tasks.py coverage) ---

    def test_auto_resolve_stuck_rides_logic(self):
        """
        WHY: Verifies the periodic maintenance logic that cancels stale rides.
        """
        from apps.rides.tasks import auto_resolve_stuck_rides

        now = timezone.now()
        # 1. Stale SEARCHING ride
        s1 = Ride.objects.create(
            rider=self.rider,
            status=Ride.Status.SEARCHING,
            pickup_lat=0,
            pickup_lng=0,
            drop_lat=0,
            drop_lng=0,
        )
        # Use update() to bypass auto_now_add=True and auto_now=True
        stale_time = now - timezone.timedelta(minutes=20)
        Ride.objects.filter(id=s1.id).update(
            created_at=stale_time, updated_at=stale_time
        )
        s1.refresh_from_db()

        auto_resolve_stuck_rides()

        s1.refresh_from_db()
        # The task cancels the stale ride via cancel_ride, verify result
        assert s1.status == Ride.Status.CANCELLED

    @patch("apps.rides.services.matching.find_driver_and_offer_ride")
    def test_retry_matching_task(self, mock_find):
        """
        WHY: Verifies the retry matcher picks up stuck SEARCHING rides.
        """
        from apps.rides.tasks import retry_matching_for_searching_rides

        Ride.objects.create(
            rider=self.rider,
            status=Ride.Status.SEARCHING,
            pickup_lat=0,
            pickup_lng=0,
            drop_lat=0,
            drop_lng=0,
        )

        retry_matching_for_searching_rides()
        mock_find.assert_called_once()
