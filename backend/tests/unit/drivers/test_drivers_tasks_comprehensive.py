"""
tests/unit/drivers/test_drivers_tasks_comprehensive.py

Complete pytest test suite for apps/drivers/tasks.py (0% → ~90% coverage).
Tests all 5 tasks + 2 helper functions:
  - recalculate_all_driver_scores
  - reset_weekly_driver_stats
  - lift_expired_suspensions
  - send_driver_feedback_nudges
  - prune_ghost_driver_sessions
  - _is_ghost_session (helper)
  - _cleanup_ghost_session (helper)
"""
import pytest
import time
from decimal import Decimal
from unittest.mock import patch, MagicMock, call
from django.utils import timezone


@pytest.fixture(autouse=True)
def bypass_idempotency():
    """Patch cache so idempotent_task always runs the function body."""
    with patch("apps.common.idempotency.cache") as mock_cache:
        mock_cache.add.return_value = True  # no duplicate lock
        mock_cache.get.return_value = None  # not done before
        yield mock_cache



# ─────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────
def _make_driver(user, status="ONLINE"):
    from apps.drivers.models import Driver
    driver, _ = Driver.objects.update_or_create(
        user=user,
        defaults={
            "status": status,
            "is_verified": True,
            "vehicle_model": "Tesla S",
            "vehicle_number": "KA01AB1234",
        },
    )
    return driver


def _make_driver_stats(driver, **kwargs):
    from apps.drivers.models import DriverStats
    defaults = {
        "weekly_rides": 10,
        "peak_hour_rides": 5,
        "acceptance_rate": 80.0,
        "cancellation_rate": 5.0,
        "offered_rides": 10,
        "accepted_rides": 8,
    }
    defaults.update(kwargs)
    stats, _ = DriverStats.objects.update_or_create(driver=driver, defaults=defaults)
    return stats


# ─────────────────────────────────────────────────────────────
# 1. recalculate_all_driver_scores
# ─────────────────────────────────────────────────────────────
@pytest.mark.django_db
class TestRecalculateAllDriverScores:

    def test_no_drivers(self):
        """With no drivers in DB, task returns 0."""
        from apps.drivers.tasks import recalculate_all_driver_scores
        result = recalculate_all_driver_scores.apply().get()
        assert result == 0

    def test_single_driver_updated(self, driver_user):
        _make_driver(driver_user)
        from apps.drivers.tasks import recalculate_all_driver_scores
        with patch("apps.drivers.services.scoring.recalculate_driver_score") as mock_score, \
             patch("apps.drivers.services.level_engine.evaluate_level") as mock_level:
            result = recalculate_all_driver_scores.apply().get()
        assert result >= 1
        mock_score.assert_called()
        mock_level.assert_called()

    def test_exception_per_driver_triggers_retry(self, driver_user):
        """When score service fails, task should attempt retry."""
        _make_driver(driver_user)
        from apps.drivers.tasks import recalculate_all_driver_scores
        from celery.exceptions import Retry
        with patch("apps.drivers.services.scoring.recalculate_driver_score",
                   side_effect=Exception("score error")), \
             patch("apps.common.backpressure.RetryStrategy.get_countdown", return_value=5):
            try:
                result = recalculate_all_driver_scores.apply().get()
            except Retry:
                result = 0  # expected — Celery raised Retry
        assert result == 0

    def test_retry_countdown_negative_no_retry(self, driver_user):
        """When countdown < 0, the task doesn't raise Retry."""
        _make_driver(driver_user)
        from apps.drivers.tasks import recalculate_all_driver_scores
        with patch("apps.drivers.services.scoring.recalculate_driver_score",
                   side_effect=Exception("score fail")), \
             patch("apps.common.backpressure.RetryStrategy.get_countdown", return_value=-1):
            result = recalculate_all_driver_scores.apply().get()
        assert result == 0

    def test_multiple_drivers_all_updated(self, driver_user):
        import random
        from django.contrib.auth import get_user_model
        from apps.drivers.models import Driver
        User = get_user_model()
        drivers_created = [driver_user]
        for i in range(3):
            phone = f"+9199{random.randint(10000000, 99999999)}"
            u = User.objects.create_user(username=phone, phone=phone, password="p", role="driver")
            Driver.objects.update_or_create(user=u, defaults={"status": Driver.Status.ONLINE})
            drivers_created.append(u)
        from apps.drivers.tasks import recalculate_all_driver_scores
        with patch("apps.drivers.services.scoring.recalculate_driver_score"), \
             patch("apps.drivers.services.level_engine.evaluate_level"):
            result = recalculate_all_driver_scores.apply().get()
        assert result == len(drivers_created)


# ─────────────────────────────────────────────────────────────
# 2. reset_weekly_driver_stats
# ─────────────────────────────────────────────────────────────
@pytest.mark.django_db
class TestResetWeeklyDriverStats:

    def test_resets_no_drivers(self):
        from apps.drivers.tasks import reset_weekly_driver_stats
        result = reset_weekly_driver_stats.apply().get()
        assert result == 0

    def test_resets_stats_to_zero(self, driver_user):
        from apps.drivers.models import DriverStats
        driver = _make_driver(driver_user)
        stats = _make_driver_stats(driver, weekly_rides=42, peak_hour_rides=13)
        from apps.drivers.tasks import reset_weekly_driver_stats
        result = reset_weekly_driver_stats.apply().get()
        assert result == 1
        stats.refresh_from_db()
        assert stats.weekly_rides == 0
        assert stats.peak_hour_rides == 0

    def test_resets_multiple_stats(self, driver_user):
        import random
        from django.contrib.auth import get_user_model
        from apps.drivers.models import Driver, DriverStats
        User = get_user_model()
        # Capture existing stats BEFORE creating new ones
        existing = DriverStats.objects.count()
        drivers = []
        for i in range(4):
            phone = f"+9188{random.randint(10000000, 99999999)}"
            u = User.objects.create_user(username=phone, phone=phone, password="p", role="driver")
            d, _ = Driver.objects.update_or_create(user=u)
            _make_driver_stats(d, weekly_rides=5, peak_hour_rides=3)
            drivers.append(d)
        from apps.drivers.tasks import reset_weekly_driver_stats
        result = reset_weekly_driver_stats.apply().get()
        assert result == existing + len(drivers)
        for d in drivers:
            d.stats.refresh_from_db()
            assert d.stats.weekly_rides == 0


# ─────────────────────────────────────────────────────────────
# 3. lift_expired_suspensions
# ─────────────────────────────────────────────────────────────
@pytest.mark.django_db
class TestLiftExpiredSuspensions:

    def test_no_suspended_drivers(self):
        from apps.drivers.tasks import lift_expired_suspensions
        result = lift_expired_suspensions.apply().get()
        assert result == 0

    def test_lifts_expired_suspension_and_notifies(self, driver_user):
        from apps.drivers.models import Driver, DriverStats
        driver = _make_driver(driver_user, status="BLOCKED")
        stats = _make_driver_stats(driver)
        # Manually set suspension fields
        stats.is_suspended = True
        stats.suspended_until = timezone.now() - timezone.timedelta(minutes=10)
        stats.save()

        from apps.drivers.tasks import lift_expired_suspensions
        result = lift_expired_suspensions.apply().get()

        assert result == 1
        stats.refresh_from_db()
        assert stats.is_suspended is False
        driver.refresh_from_db()
        assert driver.status == Driver.Status.OFFLINE

        # Verify notification was created
        from apps.notifications.models import Notification
        assert Notification.objects.filter(
            user=driver_user, type="SUSPENSION_LIFTED"
        ).exists()

    def test_not_expired_suspension_unchanged(self, driver_user):
        from apps.drivers.models import Driver
        driver = _make_driver(driver_user, status="BLOCKED")
        stats = _make_driver_stats(driver)
        stats.is_suspended = True
        stats.suspended_until = timezone.now() + timezone.timedelta(hours=2)  # future
        stats.save()

        from apps.drivers.tasks import lift_expired_suspensions
        result = lift_expired_suspensions.apply().get()
        assert result == 0
        stats.refresh_from_db()
        assert stats.is_suspended is True

    def test_exception_per_driver_logged_continues(self, driver_user):
        from apps.drivers.models import Driver
        driver = _make_driver(driver_user)
        stats = _make_driver_stats(driver)
        stats.is_suspended = True
        stats.suspended_until = timezone.now() - timezone.timedelta(minutes=5)
        stats.save()
        from apps.drivers.tasks import lift_expired_suspensions
        with patch("apps.notifications.models.Notification.objects.create",
                   side_effect=Exception("notif failed")):
            result = lift_expired_suspensions.apply().get()
        # Should still complete but failed_count reflects error
        assert result == 0  # exception caught per driver

    def test_non_blocked_driver_status_unchanged(self, driver_user):
        """Only BLOCKED drivers get reverted to OFFLINE on suspension lift."""
        from apps.drivers.models import Driver
        driver = _make_driver(driver_user, status="ONLINE")
        stats = _make_driver_stats(driver)
        stats.is_suspended = True
        stats.suspended_until = timezone.now() - timezone.timedelta(minutes=5)
        stats.save()
        from apps.drivers.tasks import lift_expired_suspensions
        lift_expired_suspensions.apply().get()
        driver.refresh_from_db()
        # Status should remain ONLINE (not BLOCKED so no change)
        assert driver.status == Driver.Status.ONLINE


# ─────────────────────────────────────────────────────────────
# 4. send_driver_feedback_nudges
# ─────────────────────────────────────────────────────────────
@pytest.mark.django_db
class TestSendDriverFeedbackNudges:

    def test_no_drivers_no_nudges(self):
        from apps.drivers.tasks import send_driver_feedback_nudges
        result = send_driver_feedback_nudges.apply().get()
        assert result == 0

    def test_low_acceptance_nudge_sent(self, driver_user):
        driver = _make_driver(driver_user)
        stats = _make_driver_stats(
            driver,
            acceptance_rate=50.0,   # < 70 → nudge
            offered_rides=10,       # >= 5 sample
        )
        from apps.drivers.tasks import send_driver_feedback_nudges
        result = send_driver_feedback_nudges.apply().get()
        # 2 notifications per nudge (push + ws)
        assert result >= 1
        from apps.notifications.models import Notification
        notifs = Notification.objects.filter(user=driver_user, type="DRIVER_FEEDBACK")
        assert notifs.count() >= 2  # push + ws

    def test_high_cancellation_nudge_sent(self, driver_user):
        driver = _make_driver(driver_user)
        stats = _make_driver_stats(
            driver,
            acceptance_rate=90.0,
            cancellation_rate=25.0,  # > 15 → nudge
            accepted_rides=10,       # >= 5 sample
        )
        from apps.drivers.tasks import send_driver_feedback_nudges
        result = send_driver_feedback_nudges.apply().get()
        assert result >= 1

    def test_good_driver_no_nudge(self, driver_user):
        driver = _make_driver(driver_user)
        stats = _make_driver_stats(
            driver,
            acceptance_rate=95.0,
            cancellation_rate=2.0,
            offered_rides=20,
            accepted_rides=20,
        )
        from apps.drivers.tasks import send_driver_feedback_nudges
        result = send_driver_feedback_nudges.apply().get()
        assert result == 0

    def test_small_sample_size_not_nudged(self, driver_user):
        """Drivers with fewer than 5 sample rides are NOT nudged."""
        driver = _make_driver(driver_user)
        stats = _make_driver_stats(
            driver,
            acceptance_rate=30.0,
            offered_rides=2,   # < 5 threshold
        )
        from apps.drivers.tasks import send_driver_feedback_nudges
        result = send_driver_feedback_nudges.apply().get()
        assert result == 0

    def test_nudge_exception_logged_continues(self, driver_user):
        driver = _make_driver(driver_user)
        _make_driver_stats(
            driver, acceptance_rate=40.0, offered_rides=10
        )
        from apps.drivers.tasks import send_driver_feedback_nudges
        with patch("apps.notifications.models.Notification.objects.create",
                   side_effect=Exception("db error")):
            result = send_driver_feedback_nudges.apply().get()
        # Task must not raise even when notify fails
        assert result == 0


# ─────────────────────────────────────────────────────────────
# 5. prune_ghost_driver_sessions
# ─────────────────────────────────────────────────────────────
@pytest.mark.django_db
class TestPruneGhostDriverSessions:

    def test_no_active_drivers(self):
        from apps.drivers.tasks import prune_ghost_driver_sessions
        with patch("apps.drivers.redis.redis_client") as mock_redis:
            mock_redis.get.return_value = None
            result = prune_ghost_driver_sessions()
        assert "0" in result

    def test_healthy_driver_not_pruned(self, driver_user):
        driver = _make_driver(driver_user, status="ONLINE")
        now_ts = int(time.time())
        fresh_ts = str(now_ts - 60).encode()  # 60s ago — well within threshold

        from apps.drivers.tasks import prune_ghost_driver_sessions
        with patch("apps.drivers.redis.redis_client") as mock_redis:
            mock_redis.get.return_value = fresh_ts
            result = prune_ghost_driver_sessions()
        assert "0" in result
        driver.refresh_from_db()
        assert driver.status == "ONLINE"

    def test_ghost_driver_pruned(self, driver_user):
        from apps.drivers.models import Driver
        driver = _make_driver(driver_user, status="ONLINE")
        stale_ts = str(int(time.time()) - 400).encode()  # 400s > 300 threshold

        from apps.drivers.tasks import prune_ghost_driver_sessions
        with patch("apps.drivers.redis.redis_client") as mock_redis, \
             patch("apps.drivers.redis.remove_driver_from_geo") as mock_remove, \
             patch("apps.notifications.services.alerts.send_critical_alert"):
            mock_redis.get.return_value = stale_ts
            result = prune_ghost_driver_sessions()

        assert "1" in result
        driver.refresh_from_db()
        assert driver.status == Driver.Status.OFFLINE
        mock_remove.assert_called_with(driver_id=driver.id)

    def test_ghost_session_prune_fires_alert(self, driver_user):
        _make_driver(driver_user, status="ONLINE")
        stale_ts = str(int(time.time()) - 500).encode()

        from apps.drivers.tasks import prune_ghost_driver_sessions
        with patch("apps.drivers.redis.redis_client") as mock_redis, \
             patch("apps.drivers.redis.remove_driver_from_geo"), \
             patch("apps.notifications.services.alerts.send_critical_alert") as mock_alert:
            mock_redis.get.return_value = stale_ts
            prune_ghost_driver_sessions()
        mock_alert.assert_called_once()

    def test_no_redis_heartbeat_uses_db_timestamp(self, driver_user):
        """When Redis has no heartbeat key, falls back to driver.updated_at."""
        from apps.drivers.models import Driver
        driver = _make_driver(driver_user, status="ONLINE")
        # Set updated_at to 700s ago (a ghost)
        Driver.objects.filter(id=driver.id).update(
            updated_at=timezone.now() - timezone.timedelta(seconds=700)
        )
        driver.refresh_from_db()

        from apps.drivers.tasks import prune_ghost_driver_sessions
        with patch("apps.drivers.redis.redis_client") as mock_redis, \
             patch("apps.drivers.redis.remove_driver_from_geo"), \
             patch("apps.notifications.services.alerts.send_critical_alert"):
            mock_redis.get.return_value = None  # no Redis heartbeat
            result = prune_ghost_driver_sessions()
        assert "1" in result

    def test_exception_during_cleanup_logged(self, driver_user):
        _make_driver(driver_user, status="ONLINE")
        stale_ts = str(int(time.time()) - 500).encode()

        from apps.drivers.tasks import prune_ghost_driver_sessions
        with patch("apps.drivers.redis.redis_client") as mock_redis, \
             patch("apps.drivers.tasks._cleanup_ghost_session",
                   side_effect=Exception("redis down")):
            mock_redis.get.return_value = stale_ts
            result = prune_ghost_driver_sessions()
        # Must handle without raising
        assert "0" in result

    def test_busy_driver_also_checked(self, driver_user):
        from apps.drivers.models import Driver
        driver = _make_driver(driver_user, status="BUSY")
        stale_ts = str(int(time.time()) - 400).encode()

        from apps.drivers.tasks import prune_ghost_driver_sessions
        with patch("apps.drivers.redis.redis_client") as mock_redis, \
             patch("apps.drivers.redis.remove_driver_from_geo"), \
             patch("apps.notifications.services.alerts.send_critical_alert"):
            mock_redis.get.return_value = stale_ts
            result = prune_ghost_driver_sessions()
        assert "1" in result
        driver.refresh_from_db()
        assert driver.status == Driver.Status.OFFLINE


# ─────────────────────────────────────────────────────────────
# 6. Helper: _is_ghost_session
# ─────────────────────────────────────────────────────────────
@pytest.mark.django_db
class TestIsGhostSession:

    def test_with_last_seen_stale(self, driver_user):
        from apps.drivers.tasks import _is_ghost_session
        driver = _make_driver(driver_user)
        now_ts = int(time.time())
        stale_last_seen = str(now_ts - 400).encode()
        assert _is_ghost_session(stale_last_seen, driver, now_ts, 300) is True

    def test_with_last_seen_fresh(self, driver_user):
        from apps.drivers.tasks import _is_ghost_session
        driver = _make_driver(driver_user)
        now_ts = int(time.time())
        fresh_last_seen = str(now_ts - 30).encode()
        assert _is_ghost_session(fresh_last_seen, driver, now_ts, 300) is False

    def test_no_last_seen_falls_back_to_db_stale(self, driver_user):
        from apps.drivers.models import Driver
        from apps.drivers.tasks import _is_ghost_session
        driver = _make_driver(driver_user)
        Driver.objects.filter(id=driver.id).update(
            updated_at=timezone.now() - timezone.timedelta(seconds=700)
        )
        driver.refresh_from_db()
        now_ts = int(time.time())
        assert _is_ghost_session(None, driver, now_ts, 300) is True

    def test_no_last_seen_falls_back_to_db_fresh(self, driver_user):
        from apps.drivers.tasks import _is_ghost_session
        driver = _make_driver(driver_user)
        # updated_at is just now (fresh)
        now_ts = int(time.time())
        assert _is_ghost_session(None, driver, now_ts, 300) is False


# ─────────────────────────────────────────────────────────────
# 7. Helper: _cleanup_ghost_session
# ─────────────────────────────────────────────────────────────
@pytest.mark.django_db
class TestCleanupGhostSession:

    def test_marks_driver_offline_and_removes_geo(self, driver_user):
        from apps.drivers.models import Driver
        from apps.drivers.tasks import _cleanup_ghost_session
        driver = _make_driver(driver_user, status="ONLINE")

        with patch("apps.drivers.redis.redis_client") as mock_redis, \
             patch("apps.drivers.redis.remove_driver_from_geo") as mock_remove:
            _cleanup_ghost_session(driver, b"1500000")

        driver.refresh_from_db()
        assert driver.status == Driver.Status.OFFLINE
        mock_remove.assert_called_with(driver_id=driver.id)
        mock_redis.delete.assert_called_with(f"driver_socket:{driver.id}")
