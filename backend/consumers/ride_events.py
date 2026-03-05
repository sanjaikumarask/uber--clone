import os
import json
import time
import django
from kafka import KafkaConsumer
from django.conf import settings
from django.db import transaction
from kafka.errors import NoBrokersAvailable

# -------------------------------------------------
# Django bootstrap
# -------------------------------------------------
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

# -------------------------------------------------
# Imports AFTER setup
# -------------------------------------------------
from apps.rides.models import Ride
from apps.drivers.models import Driver
from apps.drivers.services.geo import remove_driver_from_geo
from apps.rides.tasks import driver_accept_timeout

DRIVER_ACCEPT_TIMEOUT = getattr(settings, "RIDE_DRIVER_ACCEPT_TIMEOUT", 30)


def match_and_assign_driver(event: dict):
    if event.get("event") != "RIDE_SEARCHING":
        return

    ride_id = event.get("ride_id")
    driver_ids = event.get("driver_ids")
    attempt = event.get("attempt")

    if not ride_id or not driver_ids or attempt is None:
        print("⚠️ Invalid event:", event)
        return

    with transaction.atomic():
        ride = Ride.objects.select_for_update().get(id=ride_id)

        # -------------------------------------------------
        # IDEMPOTENCY CHECK
        # -------------------------------------------------
        if ride.search_attempt != attempt - 1:
            print(
                f"⏭ Stale event ignored for ride {ride.id} "
                f"(db={ride.search_attempt}, event={attempt})"
            )
            return

        if ride.status != Ride.Status.SEARCHING:
            print(f"⏭ Ride {ride.id} not SEARCHING")
            return

        for driver_id in driver_ids:
            driver = (
                Driver.objects
                .select_for_update()
                .filter(id=driver_id, status=Driver.Status.ONLINE)
                .first()
            )

            if not driver:
                continue

            # -------------------------------------------------
            # ATOMIC ASSIGNMENT
            # -------------------------------------------------
            from apps.rides.services.lifecycle import update_ride_status
            
            # Attach driver and update search_attempt before transition
            ride.driver = driver
            ride.search_attempt = attempt
            
            # This triggers FSM check, Driver BUSY status, and Triple Broadcast
            update_ride_status(ride, Ride.Status.OFFERED)

            driver_accept_timeout.apply_async(
                args=[ride.id, driver.id],
                countdown=DRIVER_ACCEPT_TIMEOUT,
            )

            print(f"✅ Ride {ride.id} offered to Driver {driver.id}")
            return

        print(f"❌ No available drivers for ride {ride.id}")


# -------------------------------------------------
# Kafka bootstrap with retry (IMPORTANT)
# -------------------------------------------------
while True:
    try:
        consumer = KafkaConsumer(
            "ride_events",  # MUST MATCH PRODUCER
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            api_version=(2, 6, 0),
            value_deserializer=lambda v: json.loads(v.decode("utf-8")),
            key_deserializer=lambda k: int(k.decode("utf-8")),
            auto_offset_reset="earliest",
            enable_auto_commit=True,
            group_id="ride-matcher",
        )
        break
    except NoBrokersAvailable:
        print("⏳ Kafka not ready, retrying in 5s...")
        time.sleep(5)

print("🚀 Ride Matcher Kafka Consumer started")

for message in consumer:
    event = message.value
    print("📥 Event received:", event)
    match_and_assign_driver(event)
