import pytest
from django.urls import reverse

from apps.drivers.models import Driver
from apps.payments.models import LedgerEntry
from apps.rides.models import Ride


@pytest.mark.django_db(transaction=True)
class TestRideLifecycleE2E:
    """
    E2E verification of the core ride business logic:
    Request -> Acceptance -> Arrival -> Start -> Complete -> Financial Settlement
    """

    def test_full_successful_ride_flow(
        self, auth_client, driver_client, user, driver_user, platform_user
    ):
        # 1. Rider requests a ride
        payload = {
            "pickup_lat": 12.9716,
            "pickup_lng": 77.5946,
            "pickup_address": "MG Road, Bangalore",
            "drop_lat": 12.9352,
            "drop_lng": 77.6245,
            "drop_address": "Koramangala, Bangalore",
            "vehicle_type": "go",
        }
        url = reverse("ride-list")
        print(f"DEBUG USER: id={user.id}, role={user.role}")
        auth_client.force_authenticate(user=user)
        response = auth_client.post(url, payload)
        if response.status_code != 201:
            print(f"DEBUG ERROR: {response.data}")
        assert response.status_code == 201
        ride_id = response.data["id"]

        # 2. Match calculation (simulate matching task or bypass if possible)
        ride = Ride.objects.get(id=ride_id)
        ride.candidate_driver_ids = [driver_user.driver.id]
        ride.driver = driver_user.driver  # 🔥 Assign the driver we are testing with
        ride.status = Ride.Status.OFFERED
        ride.save()

        # 3. Driver accepts the ride
        accept_url = reverse("ride-accept", kwargs={"ride_id": ride_id})
        driver_client.force_authenticate(user=driver_user)
        response = driver_client.post(accept_url)
        assert response.status_code == 200

        ride.refresh_from_db()
        assert ride.status == Ride.Status.ASSIGNED
        assert ride.driver == driver_user.driver

        # 4. Driver arrives at pickup
        arrive_url = reverse("ride-arrive", kwargs={"ride_id": ride_id})
        response = driver_client.post(arrive_url)
        assert response.status_code == 200

        ride.refresh_from_db()
        assert ride.status == Ride.Status.ARRIVED
        assert ride.otp_code is not None

        # 5. Driver starts trip (OTP verification)
        start_url = reverse("ride-start", kwargs={"ride_id": ride_id})
        response = driver_client.post(
            start_url, {"otp": ride.otp_code}
        )  # Changed otp_code to otp
        assert response.status_code == 200

        ride.refresh_from_db()
        assert ride.status == Ride.Status.ONGOING

        # 6. Driver completes trip
        complete_url = reverse("ride-complete", kwargs={"ride_id": ride_id})
        # Simulate distance/location for fare calculation
        response = driver_client.post(
            complete_url,
            {"actual_distance_km": 5.5, "end_lat": 12.9352, "end_lng": 77.6245},
        )
        assert response.status_code == 200

        ride.refresh_from_db()
        assert ride.status == Ride.Status.COMPLETED
        assert ride.final_fare > 0

        # 6.5 Rider pays for the ride (Simulated Payment)
        payment_url = reverse("payments:simulate-payment", kwargs={"ride_id": ride.id})
        auth_client.force_authenticate(user=user)
        response = auth_client.post(payment_url)
        assert response.status_code == 200
        assert response.data["status"] == "success"

        # 7. Financial Consistency Check (Ledger)
        # Rider should be debited, Driver should be credited
        rider_debits = LedgerEntry.objects.filter(
            user=user, ride_id=ride.id, entry_type=LedgerEntry.Type.DEBIT
        )
        assert rider_debits.exists()
        assert rider_debits.first().amount == ride.final_fare

        driver_credits = LedgerEntry.objects.filter(
            user=driver_user, ride_id=ride.id, entry_type=LedgerEntry.Type.CREDIT
        )
        assert driver_credits.exists()
        # net_earning should be less than final_fare (commission)
        assert driver_credits.first().amount < ride.final_fare

    def test_rider_cancellation_within_window(self, auth_client, ride, user):
        """Cancellation by rider before driver arrival should have 0 or minimal penalty."""
        # Setup: Ride is assigned to a driver
        driver = Driver.objects.first()
        ride.driver = driver
        ride.status = Ride.Status.ASSIGNED
        ride.save()

        cancel_url = reverse("ride-cancel", kwargs={"ride_id": ride.id})
        auth_client.force_authenticate(user=user)
        response = auth_client.post(cancel_url, {"reason": "Changed my mind"})
        assert response.status_code == 200

        ride.refresh_from_db()
        assert ride.status == Ride.Status.CANCELLED

        # Verify debit for cancellation (Should charge Fee since it was ASSIGNED)
        assert LedgerEntry.objects.filter(
            user=ride.rider, ride_id=ride.id, reason="rider_cancellation_fee"
        ).exists()
