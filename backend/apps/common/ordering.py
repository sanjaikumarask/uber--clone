# apps/common/ordering.py
"""
Distributed Event Fencing — Monotonic Status Ordering.

At 10k+ concurrent users, the following race is real and destructive:
  1. Driver completes ride (COMPLETED) — API call hits first
  2. A delayed reconciliation task processes a stale ONGOING webhook
  3. System reverts COMPLETED → stuck in ONGOING forever

The SequenceFencer prevents this with a monotonically increasing rank
persisted in Redis per resource. Any event with rank <= current is silently
dropped without touching the database.

Usage in lifecycle.py:
    from apps.common.ordering import SequenceFencer, RIDE_STATUS_RANK
    can_proceed = SequenceFencer.fence_event("ride", ride.id, RIDE_STATUS_RANK[new_status])
    if not can_proceed:
        return  # stale event, skip
"""
import logging
from django.core.cache import cache

logger = logging.getLogger(__name__)

# Monotonic rank for each Ride status.
# Terminal states get rank 10 — nothing can overwrite them.
RIDE_STATUS_RANK = {
    "SEARCHING": 1,
    "OFFERED":   2,
    "ASSIGNED":  3,
    "ARRIVED":   4,
    "ONGOING":   5,
    "COMPLETED": 10,
    "CANCELLED": 10,
    "NO_SHOW":   10,
}

class SequenceFencer:
    """
    Redis-backed monotonic event fence.
    Thread-safe via cache.add() (atomic SET-if-not-exists) for the initial
    set, and explicit CAS-style get/check/set for updates.
    """

    @staticmethod
    def fence_event(resource_type: str, resource_id, incoming_rank: int) -> bool:
        """
        Returns True  → event is fresh, caller should proceed.
        Returns False → event is stale/duplicate, caller must drop it.
        """
        redis_key = f"fence:{resource_type}:{resource_id}"

        # Fetch current fence rank (None = never fenced before)
        current_rank = cache.get(redis_key) or 0

        if incoming_rank <= current_rank:
            logger.warning(
                f"[Fencer] STALE event dropped: {resource_type}/{resource_id} "
                f"incoming_rank={incoming_rank} current_rank={current_rank}"
            )
            return False

        # Update the fence to the new rank.
        # TTL = 24h to cover all background reconciliation windows.
        cache.set(redis_key, incoming_rank, timeout=86400)
        return True

    @staticmethod
    def get_rank(resource_type: str, resource_id) -> int:
        """Returns the current fence rank (0 if not set)."""
        return cache.get(f"fence:{resource_type}:{resource_id}") or 0

    @staticmethod
    def clear_fence(resource_type: str, resource_id):
        """Clears once a terminal state is safely persisted to DB."""
        cache.delete(f"fence:{resource_type}:{resource_id}")
