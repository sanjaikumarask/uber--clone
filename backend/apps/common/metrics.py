# apps/common/metrics.py
from prometheus_client import Counter, Gauge, Histogram

# 🏎️ Matching Metrics
RIDE_MATCH_ATTEMPTS = Counter(
    "uber_ride_match_attempts_total",
    "Total ride matching attempts",
    ["city", "vehicle_type"],
)
RIDE_MATCH_SUCCESS = Counter(
    "uber_ride_match_success_total",
    "Successfully matched rides",
    ["city", "vehicle_type"],
)
RIDE_MATCH_LATENCY = Histogram(
    "uber_ride_match_latency_seconds",
    "Time taken to find a driver",
    buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0],
)

# 💸 Payment Metrics
PAYOUT_INITIATED = Counter(
    "uber_payout_initiated_total", "Total driver payouts initiated"
)
PAYOUT_FAILED = Counter(
    "uber_payout_failed_total", "Total failed driver payouts", ["reason"]
)

# 🌐 Infrastructure Metrics
REDIS_ERROR_COUNTER = Counter(
    "uber_redis_errors_total", "Total redis connection errors"
)
WS_CONCURRENT_RIDE_TRACKERS = Gauge(
    "uber_ws_active_trackers", "Active ride tracking websockets"
)

# 🚗 Supply Metrics
DRIVERS_ONLINE = Gauge(
    "uber_drivers_online", "Total drivers currently ONLINE", ["city"]
)
DRIVERS_BUSY = Gauge("uber_drivers_busy", "Total drivers currently on a trip", ["city"])
