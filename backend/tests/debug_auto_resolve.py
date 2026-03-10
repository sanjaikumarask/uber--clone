import uuid

import pytest
from django.utils import timezone

from apps.rides.models import Ride
from apps.rides.tasks import auto_resolve_stuck_rides
from apps.users.models import User


@pytest.mark.django_db
def test_debug_auto_resolve():
    rider = User.objects.create_user(
        username=f"rider_{uuid.uuid4().hex[:4]}", role="rider"
    )
    now = timezone.now()
    s1 = Ride.objects.create(
        rider=rider,
        status=Ride.Status.SEARCHING,
        pickup_lat=0,
        pickup_lng=0,
        drop_lat=0,
        drop_lng=0,
    )
    stale_time = now - timezone.timedelta(minutes=20)
    Ride.objects.filter(id=s1.id).update(created_at=stale_time, updated_at=stale_time)
    s1.refresh_from_db()

    print(f"\nRide updated_at: {s1.updated_at}")
    stale_threshold = timezone.now() - timezone.timedelta(minutes=15)
    print(f"Stale threshold: {stale_threshold}")
    print(f"Is updated_at < threshold? {s1.updated_at < stale_threshold}")

    stale_searching = Ride.objects.filter(
        status=Ride.Status.SEARCHING, updated_at__lt=stale_threshold
    )
    print(f"Filter count: {stale_searching.count()}")

    auto_resolve_stuck_rides()

    s1.refresh_from_db()
    print(f"Final status: {s1.status}")
    assert s1.status == Ride.Status.CANCELLED
