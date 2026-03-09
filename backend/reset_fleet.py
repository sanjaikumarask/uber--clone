import logging
import os

import django

# 1. Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from apps.drivers.models import Driver
from apps.rides.models import Ride

logger = logging.getLogger(__name__)


def reset_fleet():
    print("🚀 Resetting Fleet and Clearing Stale Tracking Data...")

    # 1. Clear Local DB Positions
    updated = Driver.objects.all().update(
        last_lat=None, last_lng=None, status=Driver.Status.OFFLINE
    )
    print(f"✅ Reset {updated} drivers to OFFLINE with no location.")

    # 2. Cancel any stray simulated rides
    ongoing = Ride.objects.filter(
        status__in=[Ride.Status.ASSIGNED, Ride.Status.ARRIVED, Ride.Status.ONGOING]
    ).update(status=Ride.Status.CANCELLED)
    print(f"✅ Cancelled {ongoing} active rides.")

    # 3. Notify Admin Map to delete all markers
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        "admin_live_map",
        {
            "type": "admin_generic_event",
            "event": "FLEET_RESET",
            "data": {"msg": "Fleet has been reset by admin"},
        },
    )
    print("✅ Notified admin Live Map of the reset.")


if __name__ == "__main__":
    reset_fleet()
