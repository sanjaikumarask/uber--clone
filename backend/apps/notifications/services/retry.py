import math

MAX_RETRIES = 5
BASE_DELAY_SECONDS = 10  # exponential base

def should_retry(notification):
    return notification.retry_count < MAX_RETRIES

def get_retry_delay(notification):
    """
    Exponential backoff:
    10s, 20s, 40s, 80s, 160s
    """
    return BASE_DELAY_SECONDS * math.pow(2, notification.retry_count)
