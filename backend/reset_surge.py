import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.rides.fare_models import FareConfig
from decimal import Decimal

updated = FareConfig.objects.filter(
    surge_multiplier__gt=Decimal("1.0")
).update(surge_multiplier=Decimal("1.0"))
print(f"Reset surge to 1.0 on {updated} FareConfig rows")

# Also clear Redis surge counters
from django.conf import settings
import redis
r = redis.Redis.from_url(settings.REDIS_URL)
keys = r.keys('surge:*') + r.keys('demand:*') + r.keys('cell:*')
if keys:
    r.delete(*keys)
    print(f"Cleared {len(keys)} surge/demand keys from Redis")
else:
    print("No surge keys in Redis")
