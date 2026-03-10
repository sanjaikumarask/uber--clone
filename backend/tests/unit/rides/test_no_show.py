from decimal import Decimal
from unittest.mock import MagicMock, patch
from django.utils import timezone
import pytest
from apps.rides.services.no_show import handle_no_show, NO_SHOW_FEE, NO_SHOW_DRIVER_PAYOUT

@pytest.fixture
def mock_ride():
    ride = MagicMock()
    ride.id = 123
    ride.status = "ARRIVED"
    ride.Status.ARRIVED = "ARRIVED"
    ride.Status.NO_SHOW = "NO_SHOW"
    ride.rider = MagicMock()
    ride.driver = MagicMock()
    ride.driver.user = MagicMock()
    return ride

@patch("apps.rides.services.no_show.Payment")
@patch("apps.rides.services.no_show.LedgerEntry")
@patch("apps.rides.services.no_show.timezone")
def test_handle_no_show_success(mock_tz, mock_ledger, mock_payment, mock_ride):
    """Should mark status as NO_SHOW and create ledger entries."""
    now = timezone.now()
    mock_tz.now.return_value = now
    
    handle_no_show(ride=mock_ride)
    
    assert mock_ride.status == "NO_SHOW"
    assert mock_ride.no_show_marked_at == now
    mock_ride.save.assert_called_once_with(update_fields=["status", "no_show_marked_at", "updated_at"])
    
    # Check payment creation
    mock_payment.objects.create.assert_called_once_with(
        user=mock_ride.rider,
        ride_id=mock_ride.id,
        amount=NO_SHOW_FEE,
        status=mock_payment.Status.CAPTURED
    )
    
    # Check ledger entries (one debit for rider, one credit for driver)
    assert mock_ledger.objects.create.call_count == 2
    
    # Rider debit
    rider_call = mock_ledger.objects.create.call_args_list[0]
    assert rider_call.kwargs["user"] == mock_ride.rider
    assert rider_call.kwargs["amount"] == NO_SHOW_FEE
    assert rider_call.kwargs["entry_type"] == mock_ledger.Type.DEBIT

    # Driver credit
    driver_call = mock_ledger.objects.create.call_args_list[1]
    assert driver_call.kwargs["user"] == mock_ride.driver.user
    assert driver_call.kwargs["amount"] == NO_SHOW_DRIVER_PAYOUT
    assert driver_call.kwargs["entry_type"] == mock_ledger.Type.CREDIT

def test_handle_no_show_wrong_status(mock_ride):
    """Should return early if ride is not in ARRIVED status."""
    mock_ride.status = "SEARCHING"
    
    with patch("apps.rides.services.no_show.Payment") as mock_pay:
        handle_no_show(ride=mock_ride)
        mock_pay.objects.create.assert_not_called()
    
    assert mock_ride.status == "SEARCHING"
