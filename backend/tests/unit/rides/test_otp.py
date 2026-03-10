import pytest
from datetime import timedelta
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from unittest.mock import MagicMock, patch

from apps.rides.services.otp import (
    _generate_otp,
    generate_and_attach_otp,
    verify_and_consume_otp
)
from apps.rides.models import Ride

@pytest.mark.django_db
class TestOTPService:

    def test_generate_otp_format(self):
        otp = _generate_otp()
        assert len(otp) == 4
        assert otp.isdigit()

    def test_generate_and_attach_otp_success(self, ride):
        ride.status = Ride.Status.ASSIGNED
        ride.otp_code = ""
        
        with patch.object(ride, 'save') as mock_save:
            otp = generate_and_attach_otp(ride)
            assert len(otp) == 4
            assert ride.otp_code == otp
            assert ride.otp_expires_at > timezone.now()
            mock_save.assert_called_once()

    def test_generate_and_attach_otp_invalid_status(self, ride):
        ride.status = Ride.Status.SEARCHING
        with pytest.raises(ValidationError) as exc:
            generate_and_attach_otp(ride)
        assert "OTP generation not allowed" in str(exc.value)

    def test_generate_and_attach_otp_already_exists(self, ride):
        ride.status = Ride.Status.ASSIGNED
        ride.otp_code = "1234"
        otp = generate_and_attach_otp(ride)
        assert otp == "1234"

    def test_verify_and_consume_otp_success(self, ride):
        ride.otp_code = "1234"
        ride.otp_expires_at = timezone.now() + timedelta(minutes=5)
        ride.otp_verified_at = None
        
        with patch.object(ride, 'save') as mock_save:
            verify_and_consume_otp(ride, "1234")
            assert ride.otp_verified_at is not None
            assert ride.otp_code == ""
            assert ride.otp_expires_at is None
            mock_save.assert_called_once()

    def test_verify_and_consume_otp_invalid(self, ride):
        ride.otp_code = "1234"
        ride.otp_expires_at = timezone.now() + timedelta(minutes=5)
        
        with pytest.raises(ValidationError) as exc:
            verify_and_consume_otp(ride, "0000")
        assert "Invalid OTP" in str(exc.value)

    def test_verify_and_consume_otp_expired(self, ride):
        ride.otp_code = "1234"
        ride.otp_expires_at = timezone.now() - timedelta(minutes=1)
        
        with pytest.raises(ValidationError) as exc:
            verify_and_consume_otp(ride, "1234")
        assert "OTP expired" in str(exc.value)

    def test_verify_and_consume_otp_none(self, ride):
        ride.otp_code = ""
        with pytest.raises(ValidationError) as exc:
            verify_and_consume_otp(ride, "1234")
        assert "OTP already used or not generated" in str(exc.value)

    def test_verify_and_consume_otp_already_verified(self, ride):
        ride.otp_code = "1234"
        ride.otp_verified_at = timezone.now()
        with pytest.raises(ValidationError) as exc:
            verify_and_consume_otp(ride, "1234")
        assert "OTP already verified" in str(exc.value)
