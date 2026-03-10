from datetime import UTC, timedelta
from unittest.mock import MagicMock, patch

from apps.drivers.services.trust import (
    apply_progressive_suspension,
    register_completed_ride,
    register_driver_cancellation,
    register_no_show,
)


@patch("apps.drivers.services.metrics.update_driver_metrics", create=True)
def test_register_completed_ride(mock_metrics):
    driver = MagicMock()
    register_completed_ride(driver)
    mock_metrics.assert_called_once_with(driver, "COMPLETED")


@patch("apps.drivers.services.trust.apply_progressive_suspension")
@patch("apps.drivers.services.metrics.update_driver_metrics", create=True)
@patch("apps.drivers.services.trust.DriverStats")
@patch("apps.drivers.services.trust.transaction.atomic")
def test_register_driver_cancellation_penalty(
    mock_atomic, mock_Stats_cls, mock_metrics, mock_suspend
):
    driver = MagicMock()
    mock_stats = MagicMock()
    mock_stats.accepted_rides = 6
    mock_stats.cancellation_rate = 50  # Over 40%
    # Mocking result of select_for_update().get()
    mock_Stats_cls.objects.select_for_update.return_value.get.return_value = mock_stats

    register_driver_cancellation(driver)

    mock_metrics.assert_called_once_with(driver, "CANCELLED")
    mock_suspend.assert_called_once_with(driver, mock_stats)


@patch("apps.drivers.services.trust.apply_progressive_suspension")
@patch("apps.drivers.services.metrics.update_driver_metrics", create=True)
@patch("apps.drivers.services.trust.DriverStats")
@patch("apps.drivers.services.trust.transaction.atomic")
def test_register_no_show_penalty(
    mock_atomic, mock_Stats_cls, mock_metrics, mock_suspend
):
    driver = MagicMock()
    mock_stats = MagicMock()
    mock_stats.no_shows = 3
    # Mocking result of select_for_update().get()
    mock_Stats_cls.objects.select_for_update.return_value.get.return_value = mock_stats

    register_no_show(driver)

    mock_metrics.assert_called_once_with(driver, "NO_SHOW")
    mock_suspend.assert_called_once_with(driver, mock_stats)


@patch("apps.notifications.models.Notification.objects.create")
@patch("apps.drivers.models.Driver.save")
@patch("apps.drivers.models.DriverStats.save")
@patch("apps.drivers.services.trust.timezone")
def test_apply_progressive_suspension_logic(
    mock_timezone, mock_stats_save, mock_driver_save, mock_notify
):
    from datetime import datetime

    now = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)
    mock_timezone.now.return_value = now

    driver = MagicMock()
    driver.status = "ONLINE"
    stats = MagicMock()
    stats.is_suspended = False
    stats.fraud_flags_count = 0  # First violation

    apply_progressive_suspension(driver, stats)

    assert stats.is_suspended is True
    assert stats.fraud_flags_count == 1
    # 1st violation = 30 min
    assert stats.suspended_until == now + timedelta(minutes=30)
    assert driver.status == "OFFLINE"
    mock_notify.assert_called_once()
