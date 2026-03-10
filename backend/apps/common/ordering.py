# apps/common/ordering.py
import logging

from apps.drivers.redis import redis_client

logger = logging.getLogger(__name__)

RIDE_STATUS_RANK = {
    "SEARCHING": 1,
    "OFFERED": 2,
    "ASSIGNED": 3,
    "ARRIVED": 4,
    "ONGOING": 5,
    "COMPLETED": 10,
    "CANCELLED": 10,
    "NO_SHOW": 10,
}


class SequenceFencer:
    """
    Redis-backed monotonic event fence.
    Utilizes Lua scripts for ATOMIC Compare-And-Swap (CAS).
    Essential for high-concurrency state machine integrity.
    """

    # Lua script to ensure: if incoming > current then current = incoming; return true
    # Else return false.
    LUA_FENCE = """
    local current = tonumber(redis.call('get', KEYS[1]) or '0')
    local incoming = tonumber(ARGV[1])
    if incoming > current then
        redis.call('set', KEYS[1], incoming)
        redis.call('expire', KEYS[1], ARGV[2])
        return 1
    end
    return 0
    """

    @classmethod
    def fence_event(cls, resource_type: str, resource_id, incoming_rank: int) -> bool:
        """
        ATOMICALLY validates and updates the event rank in Redis.
        Returns True if fresh, False if stale/duplicate.
        """
        redis_key = f"fence:{resource_type}:{resource_id}"

        # Execute Lua script for atomicity
        result = redis_client.register_script(cls.LUA_FENCE)(
            keys=[redis_key], args=[incoming_rank, 86400]  # 24h TTL
        )

        if result == 0:
            # We don't log warning here to prevent log floods on dupe events
            return False

        return True

    @classmethod
    def get_rank(cls, resource_type: str, resource_id) -> int:
        val = redis_client.get(f"fence:{resource_type}:{resource_id}")
        return int(val) if val else 0

    @classmethod
    def clear_fence(cls, resource_type: str, resource_id):
        redis_client.delete(f"fence:{resource_type}:{resource_id}")
