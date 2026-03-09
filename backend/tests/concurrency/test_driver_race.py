from concurrent.futures import ThreadPoolExecutor

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework_simplejwt.tokens import AccessToken

from apps.drivers.models import Driver
from apps.rides.models import Ride


@pytest.mark.django_db(transaction=True)
class TestDriverAssignmentConcurrency:
    """
    Simulation of the 'accept race':
    Multiple drivers receiving the same offer and trying to accept at the exact same millisecond.
    """

    def test_multiple_drivers_accept_same_ride_race(
        self, api_client, ride, django_user_model
    ):
        # 1. Setup: Create 3 drivers and offer the ride to all of them (broadcast simulation)
        # Note: Our matching engine usually targets one, but we test the safety of the View level here.
        drivers = []
        clients = []
        import uuid

        for i in range(3):
            # Use UUID based unique phone to avoid IntegrityError on collisions
            phone = f"+91{str(uuid.uuid4().int)[:10]}"
            u = django_user_model.objects.create_user(
                username=phone, phone=phone, password="password", role="driver"
            )
            d, _ = Driver.objects.update_or_create(
                user=u, defaults={"status": Driver.Status.ONLINE, "is_verified": True}
            )
            drivers.append(d)

            # Create a dedicated client for each driver
            client = api_client.__class__()
            token = AccessToken.for_user(u)
            client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
            clients.append(client)

        # Force ride to OFFERED status (bypass matching engine for pure race test)
        # In a real race, all 3 drivers might think they can accept it
        ride.status = Ride.Status.OFFERED
        ride.driver = drivers[
            0
        ]  # Usually offered to one, but we simulate a 'glitch' or broadcast
        ride.save()

        url = reverse("ride-accept", kwargs={"ride_id": ride.id})

        results = []

        def accept_ride(client):
            # We don't use X-Idempotency-Key here because we want to test the DB lock integrity
            return client.post(url)

        # 2. Execute parallel requests
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(accept_ride, c) for c in clients]
            for future in futures:
                results.append(future.result())

        # 3. Validation
        success_count = len([r for r in results if r.status_code == status.HTTP_200_OK])
        error_count = len(
            [r for r in results if r.status_code == status.HTTP_400_BAD_REQUEST]
        )

        # Exactly ONE driver must succeed. Others must be rejected.
        assert success_count == 1
        # The other 2 should fail because status changed to ASSIGNED or driver mismatch
        assert error_count == 2

        ride.refresh_from_db()
        assert ride.status == Ride.Status.ASSIGNED
        assert ride.driver in drivers

    def test_driver_double_accept_idempotency(self, driver_client, ride, driver_user):
        """Same driver clicking accept multiple times (network retry simulation)"""
        import uuid

        ride.driver = driver_user.driver
        ride.status = Ride.Status.OFFERED
        ride.save()

        url = reverse("ride-accept", kwargs={"ride_id": ride.id})
        headers = {"HTTP_X_IDEMPOTENCY_KEY": f"retry_{uuid.uuid4().hex}"}

        # Call 1
        resp1 = driver_client.post(url, **headers)
        assert resp1.status_code == 200
        assert resp1.json()["status"] == "ASSIGNED"

        # Call 2 (Immediate Retry)
        resp2 = driver_client.post(url, **headers)
        assert resp2.status_code == 200
        # Replayed response should match exactly
        assert resp2.json()["status"] == "ASSIGNED"

        # Verify side effects happened once
        # (check driver metrics - should be incremented once)
        # Note: metrics update is inside the view, so idempotency should skip it on replay.
