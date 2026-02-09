from decimal import Decimal
from django.db import transaction
from django.core.exceptions import ValidationError

from apps.supports.models import SupportTicket
from apps.payments.models import Payment
from apps.payments.services.refund import refund_payment


@transaction.atomic
def open_support_ticket(*, ride, user, reason, description=""):
    if ride.rider != user and (not ride.driver or ride.driver.user != user):
        raise ValidationError("Not allowed to open ticket for this ride")

    return SupportTicket.objects.create(
        ride=ride,
        user=user,
        reason=reason,
        description=description,
    )


@transaction.atomic
def resolve_with_refund(
    *,
    ticket: SupportTicket,
    admin,
    refund_amount: Decimal,
    reason_note: str,
):
    if not admin.is_admin:
        raise ValidationError("Admin only")

    if ticket.status != SupportTicket.Status.OPEN:
        raise ValidationError("Ticket already handled")

    payment = (
        Payment.objects
        .filter(
            ride_id=ticket.ride.id,
            status=Payment.Status.CAPTURED,
        )
        .select_for_update()
        .first()
    )

    if not payment:
        raise ValidationError("No captured payment found")

    refund_payment(
        payment=payment,
        amount=refund_amount,
        reason=f"support:{ticket.reason}",
        initiated_by=admin,
    )

    ticket.resolve(admin=admin, note=reason_note)
    return ticket


@transaction.atomic
def reject_ticket(*, ticket: SupportTicket, admin, note: str):
    if not admin.is_admin:
        raise ValidationError("Admin only")

    ticket.reject(admin=admin, note=note)
    return ticket
