import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

import redis
from django.conf import settings
from apps.drivers.models import Driver

r = redis.Redis.from_url(settings.REDIS_URL)

try:
    driver = Driver.objects.get(id=70)
    driver.status = 'ONLINE'
    driver.last_lat = 13.0827
    driver.last_lng = 80.2707
    driver.save(update_fields=['status', 'last_lat', 'last_lng'])
    print(f"Driver 70 ({driver.user.first_name}) set ONLINE in DB")
except Driver.DoesNotExist:
    print("Driver 70 not found in DB")

# Register in Redis geo index
r.geoadd('drivers:geo', [80.2707, 13.0827, '70'])

# Set heartbeat so geo search finds them
r.set(f'driver:heartbeat:70', '1', ex=3600)
r.set(f'driver:70:status', 'ONLINE', ex=3600)

total = r.zcard('drivers:geo')
print(f"Total drivers in Redis geo: {total}")
print("Bot driver 70 registered at Chennai Central (13.0827, 80.2707)")
