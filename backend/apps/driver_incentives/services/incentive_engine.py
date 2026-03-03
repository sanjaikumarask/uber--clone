import logging
import redis
from django.conf import settings
from django.utils import timezone
from django.db import transaction
from django.core.exceptions import ValidationError

from apps.driver_incentives.models import (
    DriverIncentive, DriverIncentiveProgress, DriverIncentiveEarning
)
from apps.payments.models import LedgerEntry

logger = logging.getLogger(__name__)

redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)


class IncentiveEngine:

    @staticmethod
    @transaction.atomic
    def process_ride_completion(ride):
        """
        Main entry point called when a driver completes a ride.
        Checks all active incentives and updates progress/earnings.
        """
        if not IncentiveEngine._is_valid_ride_for_incentive(ride):
            logger.info(f"Ride {ride.id} did not pass anti-abuse checks for incentives.")
            return

        driver = ride.driver
        city = getattr(ride, "city", None)
        now = timezone.now()

        incentive_qs = DriverIncentive.objects.filter(
            is_active=True,
            valid_from__lte=now,
            valid_to__gte=now,
        )

        # Filter by city if ride has one; also include global incentives (city blank/null)
        if city:
            incentive_qs = incentive_qs.filter(city__in=[city, "", None])

        for incentive in incentive_qs:
            try:
                if incentive.type == DriverIncentive.Type.STREAK:
                    IncentiveEngine._handle_streak(driver, incentive, ride)
                elif incentive.type == DriverIncentive.Type.PEAK:
                    IncentiveEngine._handle_peak(driver, incentive, ride)
                elif incentive.type == DriverIncentive.Type.ZONE:
                    IncentiveEngine._handle_zone(driver, incentive, ride)
            except Exception as e:
                logger.error(f"Error processing incentive {incentive.id} for ride {ride.id}: {e}")

    @staticmethod
    def _is_valid_ride_for_incentive(ride):
        """Anti-abuse: min distance, duration, no self-rides."""
        # Minimum 500m
        if (getattr(ride, "actual_distance_km", None) or 0) < 0.5:
            return False

        # Min 2 minutes duration
        if ride.start_time and ride.end_time:
            duration = (ride.end_time - ride.start_time).total_seconds()
            if duration < 120:
                return False

        # Self-ride check: rider == driver's user
        if ride.rider_id == getattr(ride.driver, "user_id", None):
            return False

        return True

    @staticmethod
    def _handle_streak(driver, incentive, ride):
        """
        STREAK: complete N rides → reward.
        Uses Redis counter per driver per incentive per day.
        """
        condition = incentive.condition
        required = condition.get("rides_required", 3)

        today_str = timezone.now().date().isoformat()
        redis_key = f"streak:{driver.id}:{incentive.id}:{today_str}"

        current_streak = redis_client.incr(redis_key)
        redis_client.expire(redis_key, 86400)  # Expire after 24h

        # Update DB progress record
        progress, _ = DriverIncentiveProgress.objects.get_or_create(
            driver=driver, incentive=incentive
        )
        progress.current_count = int(current_streak)
        progress.save(update_fields=["current_count", "updated_at"])

        if current_streak >= required:
            IncentiveEngine._credit_incentive(driver, incentive, ride, "Streak completed")
            # Reset streak after rewarding
            redis_client.set(redis_key, 0)
            progress.current_count = 0
            progress.completed_at = timezone.now()
            progress.save(update_fields=["current_count", "completed_at", "updated_at"])

    @staticmethod
    def _handle_peak(driver, incentive, ride):
        """PEAK: ride completed during configured time window → reward."""
        condition = incentive.condition
        start_hour = condition.get("start_hour", 17)
        end_hour = condition.get("end_hour", 20)

        local_hour = timezone.localtime(timezone.now()).hour
        if start_hour <= local_hour < end_hour:
            IncentiveEngine._credit_incentive(driver, incentive, ride, "Peak hour bonus")

    @staticmethod
    def _handle_zone(driver, incentive, ride):
        """
        ZONE: ride completed inside a geo-zone → reward.
        Supports city-based match or lat/lng bounding box.
        """
        condition = incentive.condition
        target_city = condition.get("city")

        # City-match mode
        if target_city:
            if getattr(ride, "city", None) == target_city:
                IncentiveEngine._credit_incentive(driver, incentive, ride, f"Zone bonus ({target_city})")
            return

        # Bounding-box mode: {lat_min, lat_max, lng_min, lng_max}
        lat_min = condition.get("lat_min")
        lat_max = condition.get("lat_max")
        lng_min = condition.get("lng_min")
        lng_max = condition.get("lng_max")

        if all(v is not None for v in [lat_min, lat_max, lng_min, lng_max]):
            pickup_lat = getattr(ride, "start_lat", None)
            pickup_lng = getattr(ride, "start_lng", None)

            if pickup_lat and pickup_lng:
                in_zone = (
                    lat_min <= float(pickup_lat) <= lat_max and
                    lng_min <= float(pickup_lng) <= lng_max
                )
                if in_zone:
                    IncentiveEngine._credit_incentive(driver, incentive, ride, "Geo-zone bonus")

    @staticmethod
    @transaction.atomic
    def _credit_incentive(driver, incentive, ride, reason):
        """
        Credits the reward to the driver's ledger.
        Enforces daily max_per_day limit.
        """
        today_earnings = DriverIncentiveEarning.objects.filter(
            driver=driver,
            incentive=incentive,
            created_at__date=timezone.now().date(),
        ).count()

        if today_earnings >= incentive.max_per_day:
            logger.info(
                f"Driver {driver.id} hit max_per_day ({incentive.max_per_day}) "
                f"for incentive {incentive.id}. Skipping."
            )
            return

        # ── IDEMPOTENCY GUARD ──
        # Check if already credited for THIS ride and THIS incentive
        if DriverIncentiveEarning.objects.filter(incentive=incentive, ride=ride).exists():
            logger.info(f"Driver {driver.id} already received incentive {incentive.id} for ride {ride.id}. Skipping.")
            return

        # Record earning
        DriverIncentiveEarning.objects.create(
            incentive=incentive,
            driver=driver,
            ride=ride,
            bonus_amount=incentive.reward_amount,
        )

        # Credit wallet
        LedgerEntry.objects.create(
            user=driver.user,
            ride_id=ride.id,
            amount=incentive.reward_amount,
            entry_type=LedgerEntry.Type.CREDIT,
            reason=LedgerEntry.Reason.INCENTIVE,
            reference=f"incentive:{incentive.id}_{ride.id}",
        )

        logger.info(
            f"✅ Driver {driver.id} earned ₹{incentive.reward_amount} "
            f"for '{reason}' (Incentive #{incentive.id}, Ride #{ride.id})"
        )
