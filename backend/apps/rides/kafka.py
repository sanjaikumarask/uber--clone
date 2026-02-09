# apps/rides/kafka.py

import json
from kafka import KafkaProducer
from django.conf import settings

_producer = None
TOPIC = "ride_events"


def get_producer():
    global _producer
    if _producer is None:
        _producer = KafkaProducer(
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            key_serializer=lambda k: str(k).encode("utf-8"),
            acks="all",
            retries=5,
        )
    return _producer


def _publish_event(*, ride, driver_ids):
    if not driver_ids:
        return

    producer = get_producer()

    ride.search_attempt += 1
    ride.save(update_fields=["search_attempt"])

    event = {
        "event": "RIDE_SEARCHING",
        "ride_id": ride.id,
        "driver_ids": driver_ids,
        "attempt": ride.search_attempt,
    }

    producer.send(
        TOPIC,
        key=ride.id,
        value=event,
    )
    producer.flush()


# ============================================================
# INITIAL MATCH (used by CreateRideView)
# ============================================================
def publish_ride_match_event(*, ride, driver_ids):
    _publish_event(
        ride=ride,
        driver_ids=driver_ids,
    )


# ============================================================
# RE-DISPATCH (used by Celery timeouts)
# ============================================================
def publish_ride_searching_event(*, ride, driver_ids=None):
    if not driver_ids:
        driver_ids = ride.candidate_driver_ids

    _publish_event(
        ride=ride,
        driver_ids=driver_ids,
    )
