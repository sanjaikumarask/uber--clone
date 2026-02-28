# apps/rides/fare_models.py
"""
FareConfig — Database-driven, vehicle-specific fare configuration.

Admin controls all rates from Django Admin or the Admin Dashboard API.
Values are cached in memory (60s TTL) to avoid repeated DB hits on every fare call.
"""

from decimal import Decimal
from django.db import models
from django.core.cache import cache
from django.core.validators import MinValueValidator

CACHE_KEY = "fare_config_{vehicle_type}"
CACHE_TTL = 60  # seconds


class FareConfig(models.Model):
    """
    One row per vehicle type (moto, auto, go, xl).
    Admin can update these values at any time from Django Admin.
    """

    class VehicleType(models.TextChoices):
        MOTO = "moto", "Uber Moto 🏍️"
        AUTO = "auto", "Uber Auto 🛺"
        GO   = "go",   "UberGo 🚗"
        XL   = "xl",   "UberXL 🚙"

    vehicle_type = models.CharField(
        max_length=10,
        choices=VehicleType.choices,
        unique=True,
        help_text="One config per vehicle type",
    )

    # ── FARE COMPONENTS ─────────────────────────────────────────────────
    base_fare = models.DecimalField(
        max_digits=8, decimal_places=2,
        default=Decimal("59.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Flat base charge for ANY ride (₹)",
    )
    base_distance_km = models.DecimalField(
        max_digits=5, decimal_places=2,
        default=Decimal("2.00"),
        validators=[MinValueValidator(Decimal("0.10"))],
        help_text="Distance included in base fare (km). Extra km charged separately.",
    )
    per_km_rate = models.DecimalField(
        max_digits=8, decimal_places=2,
        default=Decimal("18.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Charge per km BEYOND base_distance_km (₹/km)",
    )
    per_min_rate = models.DecimalField(
        max_digits=8, decimal_places=2,
        default=Decimal("1.50"),
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Charge per minute of ride duration (₹/min) — for fare estimation only",
    )

    # ── WAITING CHARGES ─────────────────────────────────────────────────
    waiting_free_minutes = models.PositiveSmallIntegerField(
        default=2,
        help_text="First N minutes of waiting are FREE",
    )
    waiting_per_minute = models.DecimalField(
        max_digits=6, decimal_places=2,
        default=Decimal("2.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Charge per minute AFTER free waiting period (₹/min)",
    )

    # ── SURGE ────────────────────────────────────────────────────────────
    surge_multiplier = models.DecimalField(
        max_digits=4, decimal_places=2,
        default=Decimal("1.00"),
        validators=[MinValueValidator(Decimal("1.00"))],
        help_text="Admin-controlled surge. Dynamic surge from Redis OVERRIDES this.",
    )

    # ── FLOOR ────────────────────────────────────────────────────────────
    minimum_fare = models.DecimalField(
        max_digits=8, decimal_places=2,
        default=Decimal("60.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Absolute minimum fare charged (₹)",
    )

    # ── PLATFORM ─────────────────────────────────────────────────────────
    platform_commission_pct = models.DecimalField(
        max_digits=5, decimal_places=2,
        default=Decimal("20.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Platform cut from each ride as percentage (e.g. 20.00 = 20%)",
    )

    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Fare Configuration"
        verbose_name_plural = "Fare Configurations"
        ordering = ["vehicle_type"]

    def __str__(self):
        return f"FareConfig({self.vehicle_type}) — Base ₹{self.base_fare}, ₹{self.per_km_rate}/km"

    def save(self, *args, **kwargs):
        """Bust cache on every save so new values are picked up within 1 request."""
        super().save(*args, **kwargs)
        cache.delete(CACHE_KEY.format(vehicle_type=self.vehicle_type))

    # ── CLASS METHODS ────────────────────────────────────────────────────

    @classmethod
    def get_for(cls, vehicle_type: str) -> "FareConfig":
        """
        Returns the active FareConfig for the given vehicle type.
        Falls back to 'go' if the type is not found.
        Results are cached for 60s to minimize DB calls.
        """
        cache_key = CACHE_KEY.format(vehicle_type=vehicle_type)
        cached = cache.get(cache_key)
        if cached:
            return cached

        config = (
            cls.objects.filter(vehicle_type=vehicle_type, is_active=True).first()
            or cls.objects.filter(vehicle_type=cls.VehicleType.GO, is_active=True).first()
        )

        if not config:
            # Absolute last resort: return in-memory defaults (never touches DB)
            config = cls._default(vehicle_type)

        cache.set(cache_key, config, CACHE_TTL)
        return config

    @classmethod
    def _default(cls, vehicle_type: str) -> "FareConfig":
        """Returns an unsaved default config object (fallback only)."""
        obj = cls()
        obj.vehicle_type = vehicle_type
        obj.base_fare = Decimal("59.00")
        obj.base_distance_km = Decimal("2.00")
        obj.per_km_rate = Decimal("18.00")
        obj.per_min_rate = Decimal("1.50")
        obj.waiting_free_minutes = 2
        obj.waiting_per_minute = Decimal("2.00")
        obj.surge_multiplier = Decimal("1.00")
        obj.minimum_fare = Decimal("60.00")
        obj.platform_commission_pct = Decimal("20.00")
        return obj
