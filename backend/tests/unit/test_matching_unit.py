from unittest.mock import MagicMock, patch

from apps.rides.services.matching import find_driver_and_offer_ride


@patch("apps.rides.services.matching.update_ride_status")
@patch("apps.drivers.services.metrics.update_driver_metrics", create=True)
@patch("apps.drivers.services.geo.lock_driver_for_offer", create=True)
@patch("apps.drivers.services.geo.is_driver_locked", create=True)
@patch("apps.drivers.models.DriverStats", create=True)
@patch("apps.rides.services.matching.get_nearby_driver_ids")
@patch("apps.rides.services.matching.Ride")
@patch("apps.rides.services.matching.Driver")
@patch("apps.rides.services.matching.transaction.atomic")
def test_matching_logic_success(
    mock_atomic,
    mock_Driver_cls,
    mock_Ride_cls,
    mock_geo,
    mock_stats_cls,
    mock_is_locked,
    mock_lock,
    mock_metrics,
    mock_update_status,
):
    # Setup Constants
    mock_Ride_cls.Status.SEARCHING = "SEARCHING"
    mock_Ride_cls.Status.OFFERED = "OFFERED"
    mock_Ride_cls.Status.ASSIGNED = "ASSIGNED"
    mock_Driver_cls.Status.ONLINE = "ONLINE"

    # Setup Mocks
    mock_ride = MagicMock()
    mock_ride.id = 1
    mock_ride.status = "SEARCHING"
    mock_ride.rejected_driver_ids = []
    mock_Ride_cls.objects.select_for_update.return_value.filter.return_value.first.return_value = (
        mock_ride
    )

    # Geo returns 101
    mock_geo.return_value = [101]

    # Online IDs
    mock_Driver_cls.objects.filter.return_value.values_list.return_value = [101]

    # DB Candidates
    mock_driver = MagicMock()
    mock_driver.id = 101
    mock_driver.level = "NORMAL"
    mock_Driver_cls.objects.select_for_update.return_value.select_related.return_value.filter.return_value = [
        mock_driver
    ]

    # Locks
    mock_is_locked.return_value = False
    mock_lock.return_value = True

    # Stats
    mock_stats = MagicMock()
    mock_stats.rejection_count_today = 0
    mock_stats_cls.objects.get_or_create.return_value = (mock_stats, False)

    # Call
    find_driver_and_offer_ride(1)

    # Assert success
    mock_update_status.assert_called_once_with(mock_ride, "OFFERED", driver=mock_driver)


@patch("apps.rides.services.matching.get_nearby_driver_ids")
@patch("apps.rides.services.matching.Ride")
@patch("apps.rides.services.matching.transaction.atomic")
def test_matching_no_drivers_found(mock_atomic, mock_Ride_cls, mock_geo):
    mock_Ride_cls.Status.SEARCHING = "SEARCHING"
    mock_ride = MagicMock()
    mock_ride.status = "SEARCHING"
    mock_Ride_cls.objects.select_for_update.return_value.filter.return_value.first.return_value = (
        mock_ride
    )

    mock_geo.return_value = []

    find_driver_and_offer_ride(1)
    mock_ride.save.assert_not_called()


@patch("apps.drivers.services.geo.lock_driver_for_offer", create=True)
@patch("apps.drivers.services.geo.is_driver_locked", create=True)
@patch("apps.rides.services.matching.get_nearby_driver_ids")
@patch("apps.rides.services.matching.Ride")
@patch("apps.rides.services.matching.Driver")
@patch("apps.rides.services.matching.transaction.atomic")
def test_matching_skip_rejected_drivers(
    mock_atomic, mock_Driver_cls, mock_Ride_cls, mock_geo, mock_is_locked, mock_lock
):
    mock_Ride_cls.Status.SEARCHING = "SEARCHING"
    mock_Driver_cls.Status.ONLINE = "ONLINE"

    mock_ride = MagicMock()
    mock_ride.status = "SEARCHING"
    mock_ride.rejected_driver_ids = [101]
    mock_Ride_cls.objects.select_for_update.return_value.filter.return_value.first.return_value = (
        mock_ride
    )

    # 101 rejected, 102 available
    mock_geo.return_value = [101, 102]

    # Online IDs should only include 102
    mock_Driver_cls.objects.filter.return_value.values_list.return_value = [102]

    find_driver_and_offer_ride(1)

    # Verify online filter called with 102, not 101
    args, kwargs = mock_Driver_cls.objects.filter.call_args
    assert 102 in kwargs["id__in"]
    assert 101 not in kwargs["id__in"]
