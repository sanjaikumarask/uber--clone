# apps/rides/tasks/surge.py

from celery import shared_task
from apps.common.redis import redis_client

MAX_SURGE = 3.0
SURGE_TTL = 60


@shared_task(bind=True, autoretry_for=(Exception,), retry_kwargs={"max_retries": 3})
def recompute_surge(self, cell_id: str):
    demand = int(redis_client.get(f"geo:{cell_id}:demand") or 0)
    supply = int(redis_client.get(f"geo:{cell_id}:supply") or 1)

    ratio = demand / max(supply, 1)
    surge = round(min(max(ratio, 1.0), MAX_SURGE), 2)

    redis_client.setex(
        f"geo:{cell_id}:surge",
        SURGE_TTL,
        surge,
    )

    return surge
