
import os
import django
import sys

# Add the project root to sys.path if necessary
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from apps.rides.models import Ride
from apps.rides.services.cancellation import cancel_ride

def main():
    try:
        ride_id = 47
        try:
            ride = Ride.objects.get(pk=ride_id)
        except Ride.DoesNotExist:
            print(f"Ride #{ride_id} does not exist.")
            return

        print(f"Found Ride #{ride.id} with status: {ride.status}")
        
        if ride.status == Ride.Status.CANCELLED:
            print("Ride is already cancelled.")
            return
            
        if ride.status == Ride.Status.COMPLETED:
            print("Ride is already completed and cannot be cancelled.")
            return

        print(f"Cancelling Ride #{ride.id} as SYSTEM...")
        try:
            cancel_ride(ride=ride, by=Ride.CancelledBy.SYSTEM)
            print(f"Ride #{ride.id} cancelled successfully.")
        except Exception as e:
            print(f"Error calling cancel_ride service: {e}")

    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    main()
