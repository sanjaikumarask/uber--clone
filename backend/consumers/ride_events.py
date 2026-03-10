import json
import os
import time
import logging
import django
from django.conf import settings
from django.db import transaction
from kafka import KafkaConsumer, KafkaProducer
from kafka.errors import NoBrokersAvailable

# -------------------------------------------------
# Django bootstrap
# -------------------------------------------------
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

# -------------------------------------------------
# Imports AFTER setup
# -------------------------------------------------
from apps.drivers.models import Driver
from apps.rides.models import Ride
from apps.rides.tasks import driver_accept_timeout
from apps.rides.services.lifecycle import update_ride_status

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
DLQ_TOPIC = "ride_events_dlq"
RETRY_DELAY = 1

def get_kafka_producer():
    try:
        return KafkaProducer(
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            acks=1
        )
    except Exception as e:
        logger.error(f"Failed to create Kafka Producer for DLQ: {e}")
        return None

def send_to_dlq(event, reason):
    producer = get_kafka_producer()
    if not producer:
        logger.critical(f"DLQ FAIL: Producer unavailable for event {event.get('ride_id', 'unknown')}")
        return

    payload = {
        "original_event": event,
        "reason": reason,
        "ts": time.time()
    }
    try:
        producer.send(DLQ_TOPIC, value=payload)
        producer.flush()
        logger.warning(f"Event sent to DLQ: {reason}")
    except Exception as e:
        logger.critical(f"DLQ ERROR: {e}")

def match_and_assign_driver(event: dict):
    ride_id = event.get("ride_id")
    driver_ids = event.get("driver_ids")
    attempt = event.get("attempt")

    if not ride_id or not driver_ids or attempt is None:
        logger.warning(f"Invalid matching event: {event}")
        return

    with transaction.atomic():
        try:
            ride = Ride.objects.select_for_update().get(id=ride_id)
        except Ride.DoesNotExist:
            logger.error(f"Ride {ride_id} not found")
            return

        if ride.search_attempt != attempt - 1:
            logger.info(f"Stale matching event for ride {ride.id}")
            return

        if ride.status != Ride.Status.SEARCHING:
            logger.info(f"Ride {ride.id} not SEARCHING")
            return

        for driver_id in driver_ids:
            driver = (
                Driver.objects.select_for_update()
                .filter(id=driver_id, status=Driver.Status.ONLINE)
                .first()
            )

            if not driver:
                continue

            update_ride_status(ride, Ride.Status.OFFERED, driver=driver, search_attempt=attempt)

            DRIVER_ACCEPT_TIMEOUT = getattr(settings, "RIDE_DRIVER_ACCEPT_TIMEOUT", 30)
            driver_accept_timeout.apply_async(
                args=[ride.id, driver.id],
                countdown=DRIVER_ACCEPT_TIMEOUT,
            )
            logger.info(f"Ride {ride.id} offered to Driver {driver.id}")
            return

        logger.info(f"No available drivers for ride {ride.id}")

def process_ride_event(event: dict):
    event_type = event.get("event")
    ride_id = event.get("ride_id")
    
    if not event_type or not ride_id:
        logger.error("Event missing type or ride_id")
        return

    if event_type == "RIDE_SEARCHING":
        match_and_assign_driver(event)
    elif event_type in [Ride.Status.COMPLETED, Ride.Status.CANCELLED, "ACCEPTED"]:
        target_status = Ride.Status.ASSIGNED if event_type == "ACCEPTED" else event_type
        ride = Ride.objects.get(id=ride_id)
        update_ride_status(ride, target_status)
        logger.info(f"Processed status update: {target_status} for ride {ride_id}")
    elif event_type in [Ride.Status.ONGOING, Ride.Status.ARRIVED]:
        ride = Ride.objects.get(id=ride_id)
        update_ride_status(ride, event_type)
    elif event_type == "REQUESTED": 
        ride = Ride.objects.get(id=ride_id)
        update_ride_status(ride, Ride.Status.SEARCHING)
    else:
        logger.warning(f"Unknown event type: {event_type}")

def safe_deserialize(v):
    try:
        return json.loads(v.decode("utf-8"))
    except Exception as e:
        logger.error(f"Deserialization error: {e}")
        return {"_error": "MALFORMED", "raw": str(v)}

def main():
    while True:
        try:
            consumer = KafkaConsumer(
                "ride_events",
                bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
                api_version=(2, 6, 0),
                value_deserializer=safe_deserialize,
                auto_offset_reset="earliest",
                enable_auto_commit=True,
                group_id="ride-processor-v3",
            )
            break
        except NoBrokersAvailable:
            logger.warning("Kafka not ready, retrying in 5s...")
            time.sleep(5)

    logger.info("🚀 Ride Events Kafka Consumer started")

    for message in consumer:
        event = message.value
        
        # Handle malformed JSON detected in deserializer
        if event.get("_error") == "MALFORMED":
            send_to_dlq(event, "Malformed JSON")
            continue

        retries = event.get("_retries", 0)
        try:
            process_ride_event(event)
        except Exception as e:
            logger.error(f"Processing error: {e}")
            if retries < MAX_RETRIES:
                event["_retries"] = retries + 1
                time.sleep(RETRY_DELAY * (2 ** retries))
                send_to_dlq(event, f"Transient Error: {e}")
            else:
                send_to_dlq(event, f"Max retries exceeded: {e}")
                from apps.notifications.services.alerts import send_critical_alert
                send_critical_alert(
                    title="Ride Event Processing Failed",
                    message=f"Event {event} failed after {MAX_RETRIES} retries. Error: {e}",
                    level="ERROR"
                )

if __name__ == "__main__":
    main()
