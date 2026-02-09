import json
import logging
from django.core.management.base import BaseCommand
from django.conf import settings
from kafka import KafkaConsumer

from apps.rides.services.matching import handle_ride_searching

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Kafka consumer for ride matching"

    def handle(self, *args, **kwargs):
        consumer = KafkaConsumer(
            "ride_events",
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            value_deserializer=lambda v: json.loads(v.decode("utf-8")),
            group_id="ride-matching",
            auto_offset_reset="latest",
        )

        self.stdout.write("🚀 Ride matching consumer started")

        for message in consumer:
            handle_ride_searching(message.value)
