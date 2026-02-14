# backend/apps/notifications/consumers/kafka.py

import logging
from apps.notifications.services.factory import create_and_enqueue_notification
from apps.notifications.services.registry import EVENT_REGISTRY

logger = logging.getLogger(__name__)

def handle_event(message: dict):
    """
    Entry point called by Kafka consumer loop.
    Expected message format: {"event": "DRIVER_RIDE_OFFER", "user_id": 123, "data": {...}}
    """
    event_type = message.get("event")
    user_id = message.get("user_id")
    data = message.get("data", {})

    if not event_type or not user_id:
        logger.warning(f"KAFKA_IGNORE: Invalid message format: {message}")
        return

    config = EVENT_REGISTRY.get(event_type)
    if not config:
        logger.warning(f"KAFKA_IGNORE: Unsupported event type '{event_type}'")
        return

    try:
        payload_builder = config["payload_builder"]
        payload = payload_builder(data)
    except Exception as e:
        logger.error(f"KAFKA_ERROR: Payload builder failed for {event_type}: {e}")
        return

    for channel in config["channels"]:
        create_and_enqueue_notification(
            user_id=user_id,
            event_type=event_type,
            channel=channel,
            payload=payload,
        )