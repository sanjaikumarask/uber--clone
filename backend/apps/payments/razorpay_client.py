# apps/payments/razorpay_client.py
import razorpay
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

razorpay_client = None  # ✅ ALWAYS defined

key_id = getattr(settings, "RAZORPAY_KEY_ID", None)
key_secret = getattr(settings, "RAZORPAY_KEY_SECRET", None)

if key_id and key_secret:
    razorpay_client = razorpay.Client(auth=(key_id, key_secret))
else:
    logger.warning("Razorpay client not initialized (missing credentials)")
