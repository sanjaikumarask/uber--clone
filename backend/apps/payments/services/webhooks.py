import hashlib
from django.db import IntegrityError, transaction

from apps.payments.models import WebhookEvent


def register_webhook_event(
    *,
    provider: str,
    event_id: str,
    event_type: str,
    raw_body: bytes,
) -> bool:
    """
    Returns True if event is NEW
    Returns False if DUPLICATE / REPLAY
    """

    import json
    payload = json.loads(raw_body)

    try:
        with transaction.atomic():
            WebhookEvent.objects.create(
                gateway=provider,
                event_id=event_id,
                event_type=event_type,
                payload=payload,
            )
        return True
    except IntegrityError:
        # Duplicate webhook → replay
        return False
