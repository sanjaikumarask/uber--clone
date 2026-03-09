from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from django.core.exceptions import ValidationError

from apps.supports.services import (
    open_support_ticket,
    resolve_with_refund,
    reject_ticket,
)


def _make_support_ticket(status="OPEN"):
    ticket = MagicMock()
    ticket.status = status
    ticket.Status = MagicMock()
    ticket.Status.OPEN = "OPEN"
    ticket.reason = "wrong_drop"
    return ticket


def _make_ride(rider=None, driver=None):
    ride = MagicMock()
    ride.id = 1
    ride.rider = rider or MagicMock()
    ride.driver = driver or MagicMock()
    return ride


def _make_admin(is_admin=True):
    admin = MagicMock()
    admin.is_admin = is_admin
    return admin


# ─── open_support_ticket ──────────────────────────────────────────────────────

@patch("apps.supports.services.SupportTicket")
def test_open_ticket_rider_success(mock_ticket_cls):
    user = MagicMock()
    ride = _make_ride(rider=user)

    mock_ticket_cls.objects.create.return_value = MagicMock()

    ticket = open_support_ticket(ride=ride, user=user, reason="wrong_drop")
    mock_ticket_cls.objects.create.assert_called_once_with(
        ride=ride,
        user=user,
        reason="wrong_drop",
        description="",
    )


@patch("apps.supports.services.SupportTicket")
def test_open_ticket_driver_success(mock_ticket_cls):
    driver = MagicMock()
    ride = _make_ride()
    ride.driver.user = driver

    mock_ticket_cls.objects.create.return_value = MagicMock()

    ticket = open_support_ticket(ride=ride, user=driver, reason="rider_misbehaviour", description="details")
    mock_ticket_cls.objects.create.assert_called_once()


@patch("apps.supports.services.SupportTicket")
def test_open_ticket_unauthorized_user_raises(mock_ticket_cls):
    """A random user who is not rider or driver should get a ValidationError."""
    ride = _make_ride()
    random_user = MagicMock()

    with pytest.raises(ValidationError, match="Not allowed"):
        open_support_ticket(ride=ride, user=random_user, reason="test")

    mock_ticket_cls.objects.create.assert_not_called()


# ─── resolve_with_refund ──────────────────────────────────────────────────────

@patch("apps.supports.services.refund_payment")
@patch("apps.supports.services.Payment")
def test_resolve_with_refund_success(mock_payment_cls, mock_refund):
    ticket = _make_support_ticket(status="OPEN")
    ticket.ride.id = 42
    admin = _make_admin(is_admin=True)

    mock_payment = MagicMock()
    mock_payment_cls.objects.filter.return_value.select_for_update.return_value.first.return_value = mock_payment
    mock_payment_cls.Status.CAPTURED = "CAPTURED"

    result = resolve_with_refund(
        ticket=ticket,
        admin=admin,
        refund_amount=Decimal("50.00"),
        reason_note="driver fault",
    )

    mock_refund.assert_called_once_with(
        payment=mock_payment,
        amount=Decimal("50.00"),
        reason="support:wrong_drop",
    )
    ticket.resolve.assert_called_once_with(admin=admin, note="driver fault")
    assert result == ticket


@patch("apps.supports.services.refund_payment")
@patch("apps.supports.services.Payment")
def test_resolve_with_refund_non_admin_raises(mock_payment_cls, mock_refund):
    ticket = _make_support_ticket(status="OPEN")
    non_admin = _make_admin(is_admin=False)

    with pytest.raises(ValidationError, match="Admin only"):
        resolve_with_refund(
            ticket=ticket,
            admin=non_admin,
            refund_amount=Decimal("50.00"),
            reason_note="test",
        )

    mock_refund.assert_not_called()


@patch("apps.supports.services.refund_payment")
@patch("apps.supports.services.Payment")
def test_resolve_already_handled_ticket_raises(mock_payment_cls, mock_refund):
    ticket = _make_support_ticket(status="RESOLVED")
    admin = _make_admin(is_admin=True)

    with pytest.raises(ValidationError, match="Ticket already handled"):
        resolve_with_refund(
            ticket=ticket,
            admin=admin,
            refund_amount=Decimal("50.00"),
            reason_note="test",
        )


@patch("apps.supports.services.refund_payment")
@patch("apps.supports.services.Payment")
def test_resolve_no_payment_raises(mock_payment_cls, mock_refund):
    ticket = _make_support_ticket(status="OPEN")
    admin = _make_admin(is_admin=True)

    mock_payment_cls.objects.filter.return_value.select_for_update.return_value.first.return_value = None
    mock_payment_cls.Status.CAPTURED = "CAPTURED"

    with pytest.raises(ValidationError, match="No captured payment found"):
        resolve_with_refund(
            ticket=ticket,
            admin=admin,
            refund_amount=Decimal("50.00"),
            reason_note="test",
        )

    mock_refund.assert_not_called()


# ─── reject_ticket ────────────────────────────────────────────────────────────

def test_reject_ticket_success():
    ticket = _make_support_ticket(status="OPEN")
    admin = _make_admin(is_admin=True)

    result = reject_ticket(ticket=ticket, admin=admin, note="invalid claim")

    ticket.reject.assert_called_once_with(admin=admin, note="invalid claim")
    assert result == ticket


def test_reject_ticket_non_admin_raises():
    ticket = _make_support_ticket(status="OPEN")
    non_admin = _make_admin(is_admin=False)

    with pytest.raises(ValidationError, match="Admin only"):
        reject_ticket(ticket=ticket, admin=non_admin, note="test")

    ticket.reject.assert_not_called()
