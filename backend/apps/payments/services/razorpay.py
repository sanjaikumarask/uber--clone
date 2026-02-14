# apps/payments/services/razorpay.py
import hmac
import hashlib
import logging
from django.conf import settings

logger = logging.getLogger(__name__)


def verify_razorpay_payout_webhook(*, body: bytes, signature: str) -> bool:
    """
    Verify Razorpay PAYOUT webhook signature using HMAC SHA256.
    """

    secret = getattr(settings, "RAZORPAY_PAYOUT_WEBHOOK_SECRET", None)

    if not secret:
        logger.critical("RAZORPAY_PAYOUT_WEBHOOK_SECRET is missing")
        return False

    if not signature:
        logger.warning("Missing Razorpay webhook signature")
        return False

    expected = hmac.new(
        key=secret.encode(),
        msg=body,
        digestmod=hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(expected, signature)
