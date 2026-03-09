import logging

import requests
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


def _safe_log(value: str) -> str:
    """Strip CR/LF to prevent log injection attacks."""
    return str(value).replace("\r", "").replace("\n", " ")


def send_critical_alert(title: str, message: str, level: str = "ERROR"):
    """
    Production SLA Monitor Interface.
    Dispatches critical structural errors (Fraud, Payout Failures, Redis Drops)
    to the engineering observability channels (Slack/PagerDuty).

    Level: INFO | WARNING | ERROR | CRITICAL
    """

    # 1. Format the Alert
    alert_text = (
        f"[{level}] {timezone.now().strftime('%Y-%m-%d %H:%M:%S')} - {title}\n{message}"
    )

    # Print to structure logs which Datadog/Sentry picks up natively
    safe_alert = _safe_log(alert_text)
    if level == "CRITICAL":
        logger.critical(safe_alert)
    elif level == "ERROR":
        logger.error(safe_alert)
    elif level == "WARNING":
        logger.warning(safe_alert)
    else:
        logger.info(safe_alert)

    # 1.5. Broadcast to Admin Live Map (incident panel)
    import asyncio

    try:
        channel_layer = get_channel_layer()
        if channel_layer:
            payload = {
                "type": "admin_generic_event",
                "event": "CRITICAL_ALERT",
                "data": {
                    "title": title,
                    "message": message,
                    "level": level,
                    "ts": int(timezone.now().timestamp()),
                },
            }

            try:
                loop = asyncio.get_running_loop()
                # 🚀 RUF006: We must store a reference to tasks created with create_task
                # to prevent them from being garbage collected mid-execution.
                _ = loop.create_task(channel_layer.group_send("admin_live_map", payload))
            except RuntimeError:
                # No running loop, safe to use async_to_sync
                async_to_sync(channel_layer.group_send)("admin_live_map", payload)

    except Exception:
        logger.exception("Failed to broadcast alert to admin panel")

    # 2. Transmit to Slack if Webhook configured
    webhook_url = getattr(settings, "SLACK_ALERTS_WEBHOOK_URL", None)

    if webhook_url:
        try:
            import hashlib

            from django.core.cache import cache

            # 🚨 ALERT SPAM PREVENTION: Hash the title to group identical alerts
            alert_hash = hashlib.sha256(title.encode("utf-8")).hexdigest()
            cache_key = f"alert_throttle_{alert_hash}"

            # If we already sent this exact alert type in the last 5 minutes, silently drop it
            if cache.get(cache_key):
                logger.info(f"Silenced duplicate alert: {_safe_log(title)}")
                return

            cache.set(cache_key, True, timeout=300)  # 5 minute cooldown

            payload = {
                "text": f"🚨 *{title}* 🚨\n```{message}```\n_Environment: {getattr(settings, 'ENVIRONMENT', 'production')}_"
            }
            requests.post(webhook_url, json=payload, timeout=2.0)
        except Exception:
            # We explicitly swallow the exception because if the alerting pipeline
            # goes down, we don't want it to crash the upstream business transaction.
            logger.exception("Failed to transmit Slack alert")
