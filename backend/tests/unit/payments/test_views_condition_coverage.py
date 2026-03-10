import pytest
from rest_framework import status
from rest_framework.test import APIClient
from decimal import Decimal
from unittest.mock import patch, MagicMock
from django.utils.timezone import now
from datetime import timedelta
import uuid

from apps.payments.models import Payout, LedgerEntry, Payment
from apps.drivers.models import Driver

@pytest.fixture
def api_client():
    return APIClient()

@pytest.fixture
def rider(django_user_model):
    uid = uuid.uuid4().hex[:8]
    return django_user_model.objects.create_user(username=f"rider_{uid}", role="rider")

@pytest.fixture
def driver_user(django_user_model):
    uid = uuid.uuid4().hex[:8]
    return django_user_model.objects.create_user(username=f"drvr_{uid}", role="driver")

@pytest.fixture
def driver_profile(driver_user):
    profile, _ = Driver.objects.get_or_create(
        user=driver_user, defaults={'status': Driver.Status.ONLINE, 'level': Driver.Level.NORMAL, 'is_verified': True}
    )
    profile.status = Driver.Status.ONLINE
    profile.is_verified = True
    profile.save()
    return profile

@pytest.fixture
def rider_client(api_client, rider):
    api_client.force_authenticate(user=rider)
    return api_client

@pytest.fixture
def driver_client(api_client, driver_user):
    api_client.force_authenticate(user=driver_user)
    return api_client

@pytest.mark.django_db
class TestPaymentsViewsConditionCoverage:

    # ---------------------------------------------
    # views_wallet.py
    # ---------------------------------------------
    
    def test_wallet_balance_view(self, driver_client, driver_user):
        LedgerEntry.objects.create(
            user=driver_user, amount=Decimal("1500.00"), entry_type=LedgerEntry.Type.CREDIT, reason=LedgerEntry.Reason.DRIVER_EARNING
        )
        response = driver_client.get('/api/payments/wallet/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data["total_balance"] == "1500.00"

    def test_wallet_transactions_view(self, driver_client, driver_user):
        LedgerEntry.objects.create(
            user=driver_user, amount=Decimal("1500.00"), entry_type=LedgerEntry.Type.CREDIT, reason=LedgerEntry.Reason.DRIVER_EARNING
        )
        response = driver_client.get('/api/payments/transactions/')
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]["amount"] == "1500.00"

    # ---------------------------------------------
    # views_payout.py
    # ---------------------------------------------

    def test_driver_payout_request_get_not_driver(self, rider_client):
        response = rider_client.get('/api/payments/payout/')
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data["detail"] == "Driver access only"

    def test_driver_payout_request_get_driver(self, driver_client, driver_user, driver_profile):
        LedgerEntry.objects.create(
            user=driver_user, amount=Decimal("60000.00"), entry_type=LedgerEntry.Type.CREDIT, reason=LedgerEntry.Reason.DRIVER_EARNING
        )
        Payout.objects.create(
            driver=driver_user, amount=Decimal("10000.00"), fee=Decimal("0.00"), net_amount=Decimal("10000.00"),
            status=Payout.Status.PAID, reference="ref_test"
        )
        response = driver_client.get('/api/payments/payout/')
        assert response.status_code == status.HTTP_200_OK
        assert Decimal(response.data["available_balance"]) == Decimal("60000.00")
        assert Decimal(response.data["used_today"]) == Decimal("10000.00")
        assert Decimal(response.data["remaining_limit"]) == Decimal("40000.00")
        assert response.data["can_withdraw"] is True

    def test_driver_payout_request_post_not_driver(self, rider_client):
        response = rider_client.post('/api/payments/payout/', {"amount": 500})
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_driver_payout_request_post_minimum_amount(self, driver_client, driver_profile):
        response = driver_client.post('/api/payments/payout/', {"amount": 400})
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Minimum withdrawal" in response.data["detail"]

    @patch('apps.payments.views_payout.request_driver_payout')
    @patch('apps.payments.views_payout.execute_driver_payout.delay')
    def test_driver_payout_request_post_success(self, mock_delay, mock_request_payout, driver_client, driver_user, driver_profile):
        mock_payout = MagicMock()
        mock_payout.id = 123
        mock_payout.amount = Decimal("1000.00")
        mock_payout.fee = Decimal("20.00")
        mock_payout.net_amount = Decimal("980.00")
        mock_payout.reference = "test_ref_1"
        mock_request_payout.return_value = mock_payout
        
        LedgerEntry.objects.create(
            user=driver_user, amount=Decimal("2000.00"), entry_type=LedgerEntry.Type.CREDIT, reason=LedgerEntry.Reason.DRIVER_EARNING
        )
        
        response = driver_client.post('/api/payments/payout/', {"amount": 1000})
        assert response.status_code == status.HTTP_201_CREATED
        mock_delay.assert_called_once_with(payout_id=123)

    @patch('apps.payments.views_payout.request_driver_payout')
    def test_driver_payout_request_post_value_error(self, mock_request_payout, driver_client, driver_profile):
        mock_request_payout.side_effect = ValueError("Insufficient available balance")
        response = driver_client.post('/api/payments/payout/', {"amount": 1000})
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @patch('apps.payments.views_payout.request_driver_payout')
    def test_driver_payout_request_post_exception(self, mock_request_payout, driver_client, driver_profile):
        mock_request_payout.side_effect = Exception("System Crash")
        response = driver_client.post('/api/payments/payout/', {"amount": 1000})
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

