import pytest
from decimal import Decimal
from unittest.mock import patch
from django.urls import reverse
from rest_framework import status
from apps.payments.models import Payment
import apps.payments.views_refund

@pytest.mark.django_db
class TestRefundPaymentView:
    
    @pytest.fixture
    def admin_client(self, api_client, admin_user):
        api_client.force_authenticate(user=admin_user)
        return api_client

    def test_refund_payment_success(self, admin_client, rider_user):
        payment = Payment.objects.create(
            user=rider_user,
            ride_id=1,
            amount=Decimal("100.00"),
            status=Payment.Status.CAPTURED,
            gateway_payment_id="pay_123"
        )
        url = reverse('payments:refund-payment', kwargs={'payment_id': payment.id})
        data = {"amount": "50.00", "reason": "Customer dissatisfied"}
        
        with patch('apps.payments.views_refund.refund_payment') as mock_refund:
            mock_refund.return_value = {
                "refund_id": "ref_123",
                "amount": Decimal("50.00"),
                "status": "processed"
            }
            response = admin_client.post(url, data)
            assert response.status_code == status.HTTP_200_OK
            assert response.data['refund_id'] == "ref_123"

    def test_refund_payment_invalid_payload(self, admin_client, rider_user):
        payment = Payment.objects.create(
            user=rider_user,
            ride_id=1,
            amount=Decimal("100.00"),
            status=Payment.Status.CAPTURED
        )
        url = reverse('payments:refund-payment', kwargs={'payment_id': payment.id})
        data = {"amount": "invalid"} # Should trigger exception in Decimal conversion
        
        response = admin_client.post(url, data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_refund_payment_not_found(self, admin_client):
        url = reverse('payments:refund-payment', kwargs={'payment_id': 99999})
        data = {"amount": "10.00"}
        response = admin_client.post(url, data)
        assert response.status_code == status.HTTP_404_NOT_FOUND
