from unittest.mock import MagicMock, patch
from datetime import timedelta
from django.utils import timezone
from django.core.exceptions import ValidationError
from apps.rides.services.otp import generate_and_attach_otp, verify_and_consume_otp

def test_generate_otp_success():
    # Setup Ride
    ride = MagicMock()
    # Mock status enum logic
    # The implementation checks: ride.status != ride.Status.ARRIVED
    # So we need ride.Status to have ARRIVED attribute.
    ride.Status.ARRIVED = "ARRIVED"
    ride.status = "ARRIVED"
    ride.otp_code = None
    
    otp = generate_and_attach_otp(ride)
    
    # Assert
    assert len(otp) == 4
    assert otp.isdigit()
    assert ride.otp_code == otp
    assert ride.otp_expires_at > timezone.now()
    ride.save.assert_called_once()

def test_generate_otp_wrong_state():
    ride = MagicMock()
    ride.Status.ARRIVED = "ARRIVED"
    ride.status = "SEARCHING" # Wrong state
    
    try:
        generate_and_attach_otp(ride)
        assert False
    except ValidationError:
        pass

def test_verify_otp_success():
    ride = MagicMock()
    ride.otp_code = "1234"
    ride.otp_verified_at = None
    ride.otp_expires_at = timezone.now() + timedelta(minutes=5)
    
    verify_and_consume_otp(ride, "1234")
    
    assert ride.otp_verified_at is not None
    assert ride.otp_code is None
    ride.save.assert_called_once()

def test_verify_otp_failures():
    ride = MagicMock()
    
    # CASE 1: Invalid Code
    ride.otp_code = "1234"
    ride.otp_verified_at = None
    ride.otp_expires_at = timezone.now() + timedelta(minutes=5)
    
    try:
        verify_and_consume_otp(ride, "9999")
        assert False
    except ValidationError as e:
        assert "Invalid OTP" in str(e)
        
    # CASE 2: Expired
    ride.otp_expires_at = timezone.now() - timedelta(minutes=1)
    try:
        verify_and_consume_otp(ride, "1234")
        assert False
    except ValidationError as e:
        assert "OTP expired" in str(e)
        
    # CASE 3: Already Used (cleared)
    ride.otp_code = None
    try:
        verify_and_consume_otp(ride, "1234")
        assert False
    except ValidationError as e:
        assert "OTP already used" in str(e)
