# backend/apps/notifications/providers/websocket.py

import logging
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

logger = logging.getLogger(__name__)

def send_ws(notification):
    """
    Sends the payload to the user's specific channel group.
    Group Name format: "user_{user_id}"
    """
    channel_layer = get_channel_layer()
    group_name = f"user_{notification.user.id}"
    
    logger.info(f"WS_SEND: Sending {notification.type} to {group_name}")

    try:
        async_to_sync(channel_layer.group_send)(
            group_name,
            {
                "type": "notify",  # This triggers the 'notify' method in your Consumer
                "payload": notification.payload,
                "event": notification.type, 
            },
        )
    except Exception as e:
        logger.error(f"WS_SEND ERROR: Could not send to {group_name}. Error: {e}")