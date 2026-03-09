# apps/rides/kafka.py

import json
import logging

from django.conf import settings
from kafka import KafkaProducer

logger = logging.getLogger(__name__)

_producer = None
TOPIC = "ride_events"


def get_producer():
    global _producer
    if _producer is None:
        try:
            _producer = KafkaProducer(
                bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                key_serializer=lambda k: str(k).encode("utf-8"),
                acks=1,  # Change from 'all' for faster matching latency
                retries=3,
                request_timeout_ms=5000,
            )
        except Exception as e:
            logger.error(f"Failed to initialize Kafka Producer: {e}")
            return None
    return _producer


def _publish_event(*, ride, driver_ids):
    if not driver_ids:
        return

    producer = get_producer()
    if not producer:
        logger.warning(f"Kafka producer unavailable. Skipping event for ride {ride.id}")
        return

    ride.search_attempt += 1
    ride.save(update_fields=["search_attempt"])

    event = {
        "event": "RIDE_SEARCHING",
        "ride_id": ride.id,
        "driver_ids": driver_ids,
        "attempt": ride.search_attempt,
    }

    try:
        # ASYNCHRONOUS SEND (Production Grade)
        # We do NOT call flush() here to prevent blocking the HTTP worker thread.
        producer.send(
            TOPIC,
            key=ride.id,
            value=event,
        )
    except Exception as e:
        logger.error(f"Kafka send failed for ride {ride.id}: {e}")


def publish_ride_match_event(*, ride, driver_ids):
    _publish_event(
        ride=ride,
        driver_ids=driver_ids,
    )


def publish_ride_searching_event(*, ride, driver_ids=None):
    if not driver_ids:
        driver_ids = ride.candidate_driver_ids

    _publish_event(
        ride=ride,
        driver_ids=driver_ids,
    )
