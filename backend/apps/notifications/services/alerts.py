import logging
import requests
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

def send_critical_alert(title: str, message: str, level: str = "ERROR"):
    """
    Production SLA Monitor Interface.
    Dispatches critical structural errors (Fraud, Payout Failures, Redis Drops)
    to the engineering observability channels (Slack/PagerDuty).
    
    Level: INFO | WARNING | ERROR | CRITICAL
    """
    
    # 1. Format the Alert
    alert_text = f"[{level}] {timezone.now().strftime('%Y-%m-%d %H:%M:%S')} - {title}\n{message}"
    
    # Print to structure logs which Datadog/Sentry picks up natively
    if level == "CRITICAL":
        logger.critical(alert_text)
    elif level == "ERROR":
        logger.error(alert_text)
    elif level == "WARNING":
        logger.warning(alert_text)
    else:
        logger.info(alert_text)

    # 1.5. Broadcast to Admin Live Map (incident panel)
    from channels.layers import get_channel_layer
    from asgiref.sync import async_to_sync
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
                    "ts": int(timezone.now().timestamp())
                }
            }
            
            try:
                loop = asyncio.get_running_loop()
                # We are in an async loop, use a Task or just await it if we could (but we are sync)
                # The safest for a sync function in an async loop is to schedule it
                loop.create_task(channel_layer.group_send("admin_live_map", payload))
            except RuntimeError:
                # No running loop, safe to use async_to_sync
                async_to_sync(channel_layer.group_send)("admin_live_map", payload)
                
    except Exception as e:
        logger.warning(f"Failed to broadcast alert to admin panel: {e}")

    # 2. Transmit to Slack if Webhook configured
    webhook_url = getattr(settings, "SLACK_ALERTS_WEBHOOK_URL", None)
    
    if webhook_url:
        try:
            import hashlib
            from django.core.cache import cache
            
            # 🚨 ALERT SPAM PREVENTION: Hash the title to group identical alerts
            alert_hash = hashlib.md5(title.encode('utf-8')).hexdigest()
            cache_key = f"alert_throttle_{alert_hash}"
            
            # If we already sent this exact alert type in the last 5 minutes, silently drop it
            if cache.get(cache_key):
                logger.info(f"Silenced duplicate alert: {title}")
                return
                
            cache.set(cache_key, True, timeout=300) # 5 minute cooldown
            
            payload = {
                "text": f"🚨 *{title}* 🚨\n```{message}```\n_Environment: {getattr(settings, 'ENVIRONMENT', 'production')}_"
            }
            requests.post(webhook_url, json=payload, timeout=2.0)
        except Exception as e:
            # We explicitly swallow the exception because if the alerting pipeline 
            # goes down, we don't want it to crash the upstream business transaction.
            logger.error(f"Failed to transmit Slack alert: {e}")
