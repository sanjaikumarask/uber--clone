from unittest.mock import patch, MagicMock
from decimal import Decimal
from django.core.exceptions import ValidationError
from apps.supports.services import open_support_ticket, resolve_with_refund

@patch("apps.supports.services.SupportTicket")
@patch("apps.supports.services.transaction.atomic")
def test_open_ticket_success(mock_atomic, mock_Ticket_cls):
    ride = MagicMock()
    user = MagicMock()
    ride.rider = user
    
    open_support_ticket(ride=ride, user=user, reason="reason")
    mock_Ticket_cls.objects.create.assert_called_with(
        ride=ride, user=user, reason="reason", description=""
    )

@patch("apps.supports.services.SupportTicket")
def test_open_ticket_fail_permissions(mock_Ticket_cls):
    ride = MagicMock()
    ride.rider = MagicMock() # different
    ride.driver = None
    user = MagicMock()
    
    try:
        open_support_ticket(ride=ride, user=user, reason="reason")
        assert False
    except ValidationError:
        pass

@patch("apps.supports.services.refund_payment")
@patch("apps.supports.services.Payment")
@patch("apps.supports.services.SupportTicket")
@patch("apps.supports.services.transaction.atomic")
def test_resolve_refund_success(mock_atomic, mock_Ticket_cls, mock_Payment_cls, mock_refund_svc):
    # Constants
    mock_Ticket_cls.Status.OPEN = "OPEN"
    mock_Payment_cls.Status.CAPTURED = "CAPTURED"

    admin = MagicMock()
    admin.is_admin = True
    
    ticket = MagicMock()
    ticket.status = "OPEN"
    ticket.reason = "reason"
    ticket.ride.id = 1
    
    payment = MagicMock()
    mock_Payment_cls.objects.filter.return_value.select_for_update.return_value.first.return_value = payment
    
    resolve_with_refund(
        ticket=ticket,
        admin=admin,
        refund_amount=Decimal("10.00"),
        reason_note="note"
    )
    
    mock_refund_svc.assert_called_once()
    ticket.resolve.assert_called_with(admin=admin, note="note")

@patch("apps.supports.services.SupportTicket")
def test_resolve_refund_not_admin(mock_Ticket_cls):
    admin = MagicMock()
    admin.is_admin = False
    try:
        resolve_with_refund(ticket=MagicMock(), admin=admin, refund_amount=10, reason_note="")
        assert False
    except ValidationError:
        pass
