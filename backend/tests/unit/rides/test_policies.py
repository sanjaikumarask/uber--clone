from unittest.mock import patch, MagicMock
from decimal import Decimal
from django.core.exceptions import ValidationError
from apps.rides.services.cancellation import cancel_ride
from apps.rides.services.no_show import handle_no_show

@patch("apps.rides.services.cancellation.Ride")
@patch("apps.rides.services.cancellation.Payment")
@patch("apps.rides.services.cancellation.LedgerEntry")
@patch("apps.rides.services.cancellation.transaction.atomic")
def test_cancel_ride_with_fee(mock_atomic, mock_Ledger, mock_Payment, mock_Ride_cls):
    # Setup Constants on Mock Class
    mock_Ride_cls.Status.ASSIGNED = "ASSIGNED"
    mock_Ride_cls.Status.COMPLETED = "COMPLETED"
    mock_Ride_cls.Status.CANCELLED = "CANCELLED"
    mock_Ride_cls.CancelledBy.RIDER = "RIDER"

    # Setup Ride Instance
    ride = MagicMock()
    ride.status = "ASSIGNED"
    ride.id = 1
    
    # Execution
    cancel_ride(ride=ride, by="RIDER")
    
    # Verification
    # Should charge fee
    mock_Payment.objects.create.assert_called_once()
    args, kwargs = mock_Payment.objects.create.call_args
    assert kwargs['amount'] == Decimal("25.00")
    
    mock_Ledger.objects.create.assert_called_once()
    ride.cancel.assert_called_once_with(by="RIDER")

@patch("apps.rides.services.cancellation.Ride")
@patch("apps.rides.services.cancellation.Payment")
@patch("apps.rides.services.cancellation.LedgerEntry")
@patch("apps.rides.services.cancellation.transaction.atomic")
def test_cancel_ride_no_fee(mock_atomic, mock_Ledger, mock_Payment, mock_Ride_cls):
    mock_Ride_cls.Status.SEARCHING = "SEARCHING"
    mock_Ride_cls.CancelledBy.RIDER = "RIDER"

    ride = MagicMock()
    ride.status = "SEARCHING"
    
    cancel_ride(ride=ride, by="RIDER")
    
    mock_Payment.objects.create.assert_not_called()
    ride.cancel.assert_called_once()

@patch("apps.rides.services.cancellation.Ride")
def test_cancel_ride_validation_error(mock_Ride_cls):
    mock_Ride_cls.Status.COMPLETED = "COMPLETED"
    mock_Ride_cls.Status.CANCELLED = "CANCELLED"
    
    ride = MagicMock()
    ride.status = "COMPLETED"
    
    try:
        cancel_ride(ride=ride, by="RIDER")
        assert False, "Should raise ValidationError"
    except ValidationError:
        pass

@patch("apps.rides.services.no_show.Ride")
@patch("apps.rides.services.no_show.Payment")
@patch("apps.rides.services.no_show.LedgerEntry")
@patch("apps.rides.services.no_show.transaction.atomic")
@patch("apps.rides.services.no_show.timezone")
def test_handle_no_show_success(mock_timezone, mock_atomic, mock_Ledger, mock_Payment, mock_Ride_cls):
    # Constants
    mock_Ride_cls.Status.ARRIVED = "ARRIVED"
    mock_Ride_cls.Status.NO_SHOW = "NO_SHOW"
    
    ride = MagicMock()
    ride.status = "ARRIVED"
    ride.id = 1
    
    handle_no_show(ride=ride)
    
    # Assert
    assert ride.status == "NO_SHOW"
    ride.save.assert_called_once()
    
    # Validate Payment and Ledger
    mock_Payment.objects.create.assert_called_once()
    kwargs = mock_Payment.objects.create.call_args[1]
    assert kwargs['amount'] == Decimal("50.00")
    
    # Ledger: 1 Debit (Rider), 1 Credit (Driver)
    assert mock_Ledger.objects.create.call_count == 2
