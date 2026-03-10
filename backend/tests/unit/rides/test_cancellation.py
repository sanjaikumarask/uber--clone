from decimal import Decimal
from unittest.mock import MagicMock, patch, call

import pytest
from rest_framework.exceptions import ValidationError

from apps.rides.services.cancellation import (
    cancel_ride,
    CANCEL_FEE_ASSIGNED,
    CANCEL_FEE_ARRIVED,
)


def _make_ride(status, has_driver=True):
    ride = MagicMock()
    ride.id = 42
    ride.status = status
    ride.driver = MagicMock() if has_driver else None
    ride.rider = MagicMock()
    ride.CancelledBy = MagicMock()
    ride.CancelledBy.RIDER = "RIDER"
    ride.CancelledBy.DRIVER = "DRIVER"
    ride.CancelledBy.SYSTEM = "SYSTEM"
    ride.Status.COMPLETED = "COMPLETED"
    ride.Status.CANCELLED = "CANCELLED"
    ride.Status.SEARCHING = "SEARCHING"
    ride.Status.ASSIGNED = "ASSIGNED"
    ride.Status.ARRIVED = "ARRIVED"
    ride.Status.ONGOING = "ONGOING"
    return ride


# Patch the local imports inside cancellation.py by patching at source locations
PATCHES = [
    "apps.notifications.models.Notification",
    "apps.rides.services.lifecycle._broadcast_status_update",
    "apps.payments.models.Payment",
    "apps.payments.models.LedgerEntry",
]


def test_cancel_ride_already_cancelled_raises():
    ride = _make_ride("CANCELLED")
    with pytest.raises(ValidationError, match="Ride cannot be cancelled"):
        cancel_ride(ride=ride, by="RIDER")


def test_cancel_ride_already_completed_raises():
    ride = _make_ride("COMPLETED")
    with pytest.raises(ValidationError, match="Ride cannot be cancelled"):
        cancel_ride(ride=ride, by="RIDER")


@patch("apps.notifications.models.Notification.objects")
@patch("apps.rides.services.lifecycle._broadcast_status_update")
@patch("apps.payments.models.Payment.objects")
@patch("apps.payments.models.LedgerEntry.objects")
def test_cancel_searching_ride_no_fee(mock_ledger, mock_payment, mock_broadcast, mock_notif):
    """Cancelling a SEARCHING ride should not charge any fee."""
    ride = _make_ride("SEARCHING", has_driver=False)

    cancel_ride(ride=ride, by="RIDER")

    ride.cancel.assert_called_once_with(by="RIDER")
    mock_payment.create.assert_not_called()
    mock_ledger.create.assert_not_called()
    mock_broadcast.assert_called_once_with(ride)


@patch("apps.notifications.models.Notification.objects")
@patch("apps.rides.services.lifecycle._broadcast_status_update")
@patch("apps.payments.models.LedgerEntry.objects")
@patch("apps.payments.models.Payment.objects")
def test_cancel_assigned_ride_by_rider_charges_fee(mock_payment, mock_ledger, mock_broadcast, mock_notif):
    """Cancelling ASSIGNED ride by RIDER charges CANCEL_FEE_ASSIGNED."""
    ride = _make_ride("ASSIGNED", has_driver=True)

    mock_payment_inst = MagicMock()
    mock_payment_inst.id = 99
    mock_payment.create.return_value = mock_payment_inst

    cancel_ride(ride=ride, by="RIDER")

    mock_payment.create.assert_called_once()
    call_kwargs = mock_payment.create.call_args[1]
    assert call_kwargs["amount"] == CANCEL_FEE_ASSIGNED

    mock_ledger.create.assert_called_once()
    ledger_kwargs = mock_ledger.create.call_args[1]
    assert ledger_kwargs["amount"] == CANCEL_FEE_ASSIGNED
    assert "cancel:42" in ledger_kwargs["reference"]


@patch("apps.notifications.models.Notification.objects")
@patch("apps.rides.services.lifecycle._broadcast_status_update")
@patch("apps.payments.models.LedgerEntry.objects")
@patch("apps.payments.models.Payment.objects")
def test_cancel_arrived_ride_by_rider_charges_higher_fee(mock_payment, mock_ledger, mock_broadcast, mock_notif):
    """Cancelling ARRIVED ride by RIDER charges CANCEL_FEE_ARRIVED (higher)."""
    ride = _make_ride("ARRIVED", has_driver=True)

    mock_payment.create.return_value = MagicMock(id=99)

    cancel_ride(ride=ride, by="RIDER")

    call_kwargs = mock_payment.create.call_args[1]
    assert call_kwargs["amount"] == CANCEL_FEE_ARRIVED
    assert CANCEL_FEE_ARRIVED > CANCEL_FEE_ASSIGNED


@patch("apps.drivers.services.metrics.update_driver_metrics")
@patch("apps.notifications.models.Notification.objects")
@patch("apps.rides.services.lifecycle._broadcast_status_update")
@patch("apps.payments.models.LedgerEntry.objects")
@patch("apps.payments.models.Payment.objects")
def test_driver_cancel_triggers_penalty(mock_payment, mock_ledger, mock_broadcast, mock_notif, mock_update_metrics):
    """Cancelling by DRIVER triggers trust score penalty."""
    ride = _make_ride("ASSIGNED", has_driver=True)

    cancel_ride(ride=ride, by="DRIVER")

    mock_update_metrics.assert_called_once_with(ride.driver, "CANCELLED")


@patch("apps.notifications.models.Notification.objects")
@patch("apps.rides.services.lifecycle._broadcast_status_update")
@patch("apps.payments.models.LedgerEntry.objects")
@patch("apps.payments.models.Payment.objects")
def test_driver_released_on_cancel(mock_payment, mock_ledger, mock_broadcast, mock_notif):
    """Driver status is set back to ONLINE when ride is cancelled."""
    ride = _make_ride("ASSIGNED", has_driver=True)

    with patch("apps.drivers.models.Driver.Status") as mock_driver_status:
        mock_driver_status.ONLINE = "ONLINE"
        cancel_ride(ride=ride, by="SYSTEM")

    assert ride.driver.status == "ONLINE"
    ride.driver.save.assert_called_once_with(update_fields=["status"])


@patch("apps.notifications.models.Notification.objects")
@patch("apps.rides.services.lifecycle._broadcast_status_update")
@patch("apps.payments.models.LedgerEntry.objects")
@patch("apps.payments.models.Payment.objects")
def test_both_rider_and_driver_notified(mock_payment, mock_ledger, mock_broadcast, mock_notif):
    """Both rider and driver should receive a notification on cancellation."""
    ride = _make_ride("ASSIGNED", has_driver=True)

    cancel_ride(ride=ride, by="RIDER")

    # Two Notification.objects.create() calls: one for rider, one for driver
    assert mock_notif.create.call_count == 2


@patch("apps.notifications.models.Notification.objects")
@patch("apps.rides.services.lifecycle._broadcast_status_update")
@patch("apps.payments.models.LedgerEntry.objects")
@patch("apps.payments.models.Payment.objects")
def test_no_driver_notification_when_no_driver(mock_payment, mock_ledger, mock_broadcast, mock_notif):
    """If no driver assigned, only rider gets notification."""
    ride = _make_ride("SEARCHING", has_driver=False)

    cancel_ride(ride=ride, by="RIDER")

    # Only one call: for the rider
    assert mock_notif.create.call_count == 1
