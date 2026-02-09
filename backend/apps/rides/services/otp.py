# apps/rides/services/otp.py

import random
from datetime import timedelta
from django.utils import timezone
from django.core.exceptions import ValidationError

OTP_EXPIRY_MINUTES = 5


def _generate_otp():
    return f"{random.randint(1000, 9999)}"


def generate_and_attach_otp(ride):
    if ride.status != ride.Status.ARRIVED:
        raise ValidationError("OTP allowed only in ARRIVED state")

    if ride.otp_code:
        return ride.otp_code

    ride.otp_code = _generate_otp()
    ride.otp_expires_at = timezone.now() + timedelta(minutes=OTP_EXPIRY_MINUTES)
    ride.otp_verified_at = None

    ride.save(update_fields=[
        "otp_code",
        "otp_expires_at",
        "otp_verified_at",
    ])
    return ride.otp_code


def verify_and_consume_otp(ride, otp: str):
    if not ride.otp_code:
        raise ValidationError("OTP already used or not generated")

    if ride.otp_verified_at:
        raise ValidationError("OTP already verified")

    if not ride.otp_expires_at or timezone.now() > ride.otp_expires_at:
        raise ValidationError("OTP expired")

    if ride.otp_code != otp:
        raise ValidationError("Invalid OTP")

    ride.otp_verified_at = timezone.now()
    ride.otp_code = None
    ride.otp_expires_at = None

    ride.save(update_fields=[
        "otp_verified_at",
        "otp_code",
        "otp_expires_at",
    ])
