from unittest.mock import MagicMock, patch
from datetime import timedelta
from django.utils import timezone
import pytest
from rest_framework.exceptions import ValidationError
from apps.rides.services.otp import generate_and_attach_otp, verify_and_consume_otp

def test_generate_otp_success():
    # Setup Ride
    ride = MagicMock()
    # Mock status enum logic
    # The implementation checks: ride.status not in [ride.Status.ASSIGNED, ride.Status.ARRIVED]
    ride.Status.ARRIVED = "ARRIVED"
    ride.Status.ASSIGNED = "ASSIGNED"
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
    ride.Status.ASSIGNED = "ASSIGNED"
    ride.status = "SEARCHING" # Wrong state
    
    with pytest.raises(ValidationError) as excinfo:
        generate_and_attach_otp(ride)
    assert "OTP generation not allowed" in str(excinfo.value)

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
    
    with pytest.raises(ValidationError) as excinfo:
        verify_and_consume_otp(ride, "9999")
    assert "Invalid OTP" in str(excinfo.value)
        
    # CASE 2: Expired
    ride.otp_expires_at = timezone.now() - timedelta(minutes=1)
    with pytest.raises(ValidationError) as excinfo:
        verify_and_consume_otp(ride, "1234")
    assert "OTP expired" in str(excinfo.value)
        
    # CASE 3: Already Used (cleared)
    ride.otp_code = None
    with pytest.raises(ValidationError) as excinfo:
        verify_and_consume_otp(ride, "1234")
    assert "already used" in str(excinfo.value)
