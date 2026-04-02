import django
import os
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from apps.rides.models import Ride
from apps.drivers.models import Driver
from apps.users.models import User
from apps.rides.services.lifecycle import update_ride_status
from apps.rides.services.complete_ride import complete_ride

# Ensure driver 70 exists
d = Driver.objects.filter(id=70).first()
if not d:
    u, _ = User.objects.get_or_create(username='bot70', defaults={'role': 'driver'})
    d, _ = Driver.objects.get_or_create(id=70, defaults={'user': u})
    d.status = "ONLINE"
    d.save()

# Get or create rider
r, _ = User.objects.get_or_create(username='test_rider', defaults={'role': 'rider'})

# Create ride
ride = Ride.objects.create(
    rider=r,
    pickup_lat=0.0, pickup_lng=0.0,
    drop_lat=1.0, drop_lng=1.0,
    status="SEARCHING"
)

print("Ride created")
ride.driver = d
ride.save(update_fields=['driver'])
update_ride_status(ride, "ASSIGNED")
update_ride_status(ride, "ARRIVED")
ride.start_lat, ride.start_lng = ride.pickup_lat, ride.pickup_lng
ride.save(update_fields=["start_lat", "start_lng"])
update_ride_status(ride, "ONGOING")

print("Ride ongoing, completing...")
try:
    complete_ride(ride.id)
    print("SUCCESS: Ride completed without raising 'Must be User instance'")
except Exception as e:
    print("ERROR DURING COMPLETION:", type(e), e)
