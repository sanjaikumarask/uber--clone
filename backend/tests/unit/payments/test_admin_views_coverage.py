import pytest
from decimal import Decimal
from django.utils.timezone import now
import uuid
from rest_framework.test import APIRequestFactory, force_authenticate
from unittest.mock import patch

from apps.payments.models import LedgerEntry, Payout
from apps.payments.admin_views import (
    AdminPaymentsView, AdminPayoutListView, 
    AdminApprovePayoutView, AdminRejectPayoutView, AdminLedgerCheckView
)
from apps.drivers.models import Driver

@pytest.fixture
def factory():
    return APIRequestFactory()

@pytest.fixture
def admin_user(django_user_model):
    uid = uuid.uuid4().hex[:8]
    return django_user_model.objects.create_user(username=f"admin_{uid}", role="admin")

@pytest.fixture
def driver_user(django_user_model):
    uid = uuid.uuid4().hex[:8]
    return django_user_model.objects.create_user(username=f"driver_{uid}", role="driver")

@pytest.fixture
def driver_profile(driver_user):
    profile, _ = Driver.objects.get_or_create(
        user=driver_user, defaults={'status': Driver.Status.ONLINE, 'level': Driver.Level.NORMAL, 'is_verified': True}
    )
    return profile

@pytest.mark.django_db
class TestPaymentsAdminViewsCoverage:

    def test_admin_payments_view(self, factory, admin_user, driver_user):
        LedgerEntry.objects.create(
            user=driver_user, amount=Decimal("150.00"), entry_type=LedgerEntry.Type.CREDIT,
            reason=LedgerEntry.Reason.DRIVER_EARNING
        )
        request = factory.get('/fake/')
        force_authenticate(request, user=admin_user)
        view = AdminPaymentsView.as_view()
        response = view(request)
        assert response.status_code == 200
        assert len(response.data) == 1

    def test_admin_payout_list_view(self, factory, admin_user, driver_user, driver_profile):
        Payout.objects.create(
            driver=driver_user, amount=Decimal("100.00"), fee=Decimal("0.00"),
            net_amount=Decimal("100.00"), status=Payout.Status.REQUESTED
        )
        request = factory.get('/fake/')
        force_authenticate(request, user=admin_user)
        view = AdminPayoutListView.as_view()
        response = view(request)
        assert response.status_code == 200
        assert len(response.data) == 1

    @patch('apps.payments.admin_views.execute_driver_payout.delay')
    def test_admin_approve_payout_success(self, mock_delay, factory, admin_user, driver_user):
        payout = Payout.objects.create(
            driver=driver_user, amount=Decimal("100.00"), fee=Decimal("0.00"),
            net_amount=Decimal("100.00"), status=Payout.Status.REQUESTED
        )
        request = factory.post('/fake/')
        force_authenticate(request, user=admin_user)
        view = AdminApprovePayoutView.as_view()
        response = view(request, payout_id=payout.id)
        assert response.status_code == 200
        mock_delay.assert_called_once_with(payout.id)
        payout.refresh_from_db()
        assert payout.status == Payout.Status.PROCESSING

    def test_admin_approve_payout_invalid_state(self, factory, admin_user, driver_user):
        payout = Payout.objects.create(
            driver=driver_user, amount=Decimal("100.00"), fee=Decimal("0.00"),
            net_amount=Decimal("100.00"), status=Payout.Status.PAID
        )
        request = factory.post('/fake/')
        force_authenticate(request, user=admin_user)
        view = AdminApprovePayoutView.as_view()
        response = view(request, payout_id=payout.id)
        assert response.status_code == 400

    def test_admin_reject_payout_success(self, factory, admin_user, driver_user):
        payout = Payout.objects.create(
            driver=driver_user, amount=Decimal("100.00"), fee=Decimal("0.00"),
            net_amount=Decimal("100.00"), status=Payout.Status.REQUESTED
        )
        request = factory.post('/fake/')
        force_authenticate(request, user=admin_user)
        view = AdminRejectPayoutView.as_view()
        response = view(request, payout_id=payout.id)
        assert response.status_code == 200
        payout.refresh_from_db()
        assert payout.status == Payout.Status.FAILED

    def test_admin_reject_payout_invalid_state(self, factory, admin_user, driver_user):
        payout = Payout.objects.create(
            driver=driver_user, amount=Decimal("100.00"), fee=Decimal("0.00"),
            net_amount=Decimal("100.00"), status=Payout.Status.PAID
        )
        request = factory.post('/fake/')
        force_authenticate(request, user=admin_user)
        view = AdminRejectPayoutView.as_view()
        response = view(request, payout_id=payout.id)
        assert response.status_code == 400

    def test_admin_ledger_check_success(self, factory, admin_user, driver_user):
        request = factory.post('/fake/', {"user_id": driver_user.id})
        force_authenticate(request, user=admin_user)
        view = AdminLedgerCheckView.as_view()
        response = view(request)
        assert response.status_code == 200

    def test_admin_ledger_check_missing_user_id(self, factory, admin_user):
        request = factory.post('/fake/')
        force_authenticate(request, user=admin_user)
        view = AdminLedgerCheckView.as_view()
        response = view(request)
        assert response.status_code == 400

    def test_admin_ledger_check_user_not_found(self, factory, admin_user):
        request = factory.post('/fake/', {"user_id": 99999})
        force_authenticate(request, user=admin_user)
        view = AdminLedgerCheckView.as_view()
        response = view(request)
        assert response.status_code == 404

