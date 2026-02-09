# apps/rides/fare_config.py
from decimal import Decimal

# =========================
# BASE FARE CONFIG
# =========================

BASE_FARE = Decimal("40.00")          # ₹40 flat
PER_KM_RATE = Decimal("12.00")        # ₹12 per km
PER_MIN_RATE = Decimal("1.50")        # ₹1.50 per minute

MINIMUM_FARE = Decimal("60.00")       # hard floor

# =========================
# PLATFORM ECONOMICS
# =========================

# % cut taken by platform from total fare
PLATFORM_COMMISSION_PERCENT = Decimal("20.0")  # 20%

# =========================
# IMPORTANT NOTES
# =========================
# ❌ NO SURGE MULTIPLIER HERE
# Surge is DYNAMIC and must be fetched from Redis:
#   apps.rides.services.surge.get_surge_multiplier()
#
# Fare formula (final):
# (BASE + distance + duration) * surge
#
# Surge must be applied EXACTLY ONCE
