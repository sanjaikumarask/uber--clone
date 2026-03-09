from unittest.mock import MagicMock, patch, ANY
from datetime import timedelta

import pytest
from django.utils import timezone

from apps.drivers.models import Driver, DriverStats
from apps.drivers.tasks import (
    recalculate_all_driver_scores,
    reset_weekly_driver_stats,
    lift_expired_suspensions,
    send_driver_feedback_nudges,
    prune_ghost_driver_sessions
)

@pytest.mark.django_db
class TestDriverTasks:

    def test_recalculate_all_driver_scores(self, driver_user):
        # Patching the original services because they are locally imported in the task
        with patch("apps.drivers.services.scoring.recalculate_driver_score") as mock_score:
            with patch("apps.drivers.services.level_engine.evaluate_level") as mock_level:
                updated = recalculate_all_driver_scores()
                assert updated == 1
                mock_score.assert_called_once()
                mock_level.assert_called_once()

    def test_reset_weekly_driver_stats(self, driver_user):
        stats = DriverStats.objects.get(driver=driver_user.driver)
        stats.weekly_rides = 10
        stats.peak_hour_rides = 5
        stats.save()
        
        count = reset_weekly_driver_stats()
        assert count == 1
        stats.refresh_from_db()
        assert stats.weekly_rides == 0
        assert stats.peak_hour_rides == 0

    def test_lift_expired_suspensions(self, driver_user):
        driver = driver_user.driver
        stats = DriverStats.objects.get(driver=driver)
        stats.is_suspended = True
        stats.suspended_until = timezone.now() - timedelta(minutes=1)
        stats.save()
        
        driver.status = Driver.Status.BLOCKED
        driver.save()
        
        lifted = lift_expired_suspensions()
        assert lifted == 1
        
        stats.refresh_from_db()
        assert stats.is_suspended is False
        
        driver.refresh_from_db()
        assert driver.status == Driver.Status.OFFLINE

    def test_send_driver_feedback_nudges(self, driver_user):
        stats = DriverStats.objects.get(driver=driver_user.driver)
        stats.acceptance_rate = 50.0
        stats.offered_rides = 10
        stats.cancellation_rate = 20.0
        stats.accepted_rides = 10
        stats.save()
        
        from apps.notifications.models import Notification
        
        count = send_driver_feedback_nudges()
        assert count >= 2 # One for low acceptance, one for high cancellation
        
        assert Notification.objects.filter(user=driver_user, type="DRIVER_FEEDBACK").exists()

    @patch("apps.drivers.redis.redis_client")
    def test_prune_ghost_driver_sessions(self, mock_redis, driver_user):
        driver = driver_user.driver
        driver.status = Driver.Status.ONLINE
        driver.save()
        
        # Scenario: Last seen 10 minutes ago
        import time
        now_ts = int(time.time())
        mock_redis.get.return_value = str(now_ts - 600)
        
        with patch("apps.notifications.services.alerts.send_critical_alert") as mock_alert:
            res = prune_ghost_driver_sessions()
            assert "Pruned 1" in res
            
            driver.refresh_from_db()
            assert driver.status == Driver.Status.OFFLINE
            mock_alert.assert_called_once()
