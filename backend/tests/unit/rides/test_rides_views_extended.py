import pytest
from decimal import Decimal
from django.urls import reverse
from rest_framework import status
from apps.rides.models import Ride, RideFeedback
from apps.payments.models import Payment, DriverEarnings, LedgerEntry
from apps.notifications.models import Notification
from apps.drivers.models import Driver, DriverStats
from apps.users.models import RiderStats
import apps.rides.views

@pytest.mark.django_db
class TestRidesViewsExtended:

    def test_ride_fare_breakdown_permission_denied(self, authenticated_rider_client, rider_user, ride, driver_user):
        # Create a ride for a different rider
        # 'ride' fixture uses 'user' fixture which might be different from 'rider_user'
        # Let's ensure the ride is NOT owned by rider_user
        ride.rider = driver_user 
        ride.status = Ride.Status.COMPLETED
        ride.save()
        
        url = reverse('ride-fare-breakdown', kwargs={'ride_id': ride.id})
        # authenticated_rider_client is already authenticated as rider_user
        response = authenticated_rider_client.get(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_ride_fare_breakdown_not_completed(self, authenticated_rider_client, rider_user, ride):
        ride.rider = rider_user
        ride.status = Ride.Status.ONGOING
        ride.save()
        
        url = reverse('ride-fare-breakdown', kwargs={'ride_id': ride.id})
        response = authenticated_rider_client.get(url)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "only available for completed rides" in response.data['error']

    def test_tip_view_success(self, django_capture_on_commit_callbacks, authenticated_rider_client, rider_user, ride, driver_user):
        # Setup: Completed ride with captured payment
        ride.rider = rider_user
        ride.status = Ride.Status.COMPLETED
        ride.driver = driver_user.driver
        ride.final_fare = Decimal("150.00")
        ride.save()
        
        Payment.objects.create(
            ride_id=ride.id,
            user=ride.rider,
            amount=ride.final_fare or Decimal("100.00"),
            status=Payment.Status.CAPTURED,
            gateway_payment_id="pay_123"
        )
        
        url = reverse('ride-tip', kwargs={'ride_id': ride.id})
        
        data = {"tip_amount": 50.00}
        with django_capture_on_commit_callbacks(execute=True):
            response = authenticated_rider_client.post(url, data)
        
        assert response.status_code == status.HTTP_200_OK
        ride.refresh_from_db()
        assert ride.tip_amount == Decimal("50.00")
        
        # Verify Earnings and Ledger
        earning = DriverEarnings.objects.get(ride=ride)
        assert earning.amount == Decimal("50.00")
        
        ledger = LedgerEntry.objects.filter(ride_id=ride.id, reason=LedgerEntry.Reason.DRIVER_EARNING).first()
        assert ledger.amount == Decimal("50.00")
        
        # Verify Notification
        assert Notification.objects.filter(user=driver_user, type="TIP_RECEIVED").exists()

    def test_tip_view_invalid_amount(self, authenticated_rider_client, rider_user, ride):
        ride.rider = rider_user
        ride.save()
        url = reverse('ride-tip', kwargs={'ride_id': ride.id})
        
        # Negative tip
        response = authenticated_rider_client.post(url, {"tip_amount": -10})
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        
        # Exceeds max
        response = authenticated_rider_client.post(url, {"tip_amount": 2000})
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_tip_view_no_payment(self, authenticated_rider_client, rider_user, ride, driver_user):
        ride.rider = rider_user
        ride.status = Ride.Status.COMPLETED
        ride.driver = driver_user.driver
        ride.final_fare = Decimal("150.00")
        ride.save()
        
        url = reverse('ride-tip', kwargs={'ride_id': ride.id})
        
        response = authenticated_rider_client.post(url, {"tip_amount": 50})
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "complete payment before" in response.data['error']

    def test_tip_view_wrong_rider(self, authenticated_driver_client, ride):
        # Driver trying to tip (should be blocked by IsRider permission)
        url = reverse('ride-tip', kwargs={'ride_id': ride.id})
        
        response = authenticated_driver_client.post(url, {"tip_amount": 50})
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_submit_feedback_rider_to_driver(self, authenticated_rider_client, rider_user, ride, driver_user):
        ride.rider = rider_user
        ride.status = Ride.Status.COMPLETED
        ride.driver = driver_user.driver
        ride.save()
        DriverStats.objects.get_or_create(driver=driver_user.driver)
        
        url = reverse('ride-feedback', kwargs={'ride_id': ride.id})
        
        data = {"rating": 5, "comment": "Great ride!"}
        response = authenticated_rider_client.post(url, data)
        assert response.status_code == status.HTTP_200_OK
        assert RideFeedback.objects.filter(ride=ride, giver_role="RIDER").exists()

    def test_submit_feedback_driver_to_rider(self, authenticated_driver_client, driver_user, ride, rider_user):
        ride.rider = rider_user
        ride.status = Ride.Status.COMPLETED
        ride.driver = driver_user.driver
        ride.save()
        RiderStats.objects.get_or_create(user=ride.rider)
        
        url = reverse('ride-feedback', kwargs={'ride_id': ride.id})
        
        data = {"rating": 4, "comment": "Polite passenger"}
        response = authenticated_driver_client.post(url, data)
        assert response.status_code == status.HTTP_200_OK
        assert RideFeedback.objects.filter(ride=ride, giver_role="DRIVER").exists()

    def test_nearby_drivers_view(self, api_client, driver_user):
        driver = driver_user.driver
        driver.status = Driver.Status.ONLINE
        driver.last_lat = 12.9716
        driver.last_lng = 77.5946
        driver.save()
        
        url = reverse('ride-nearby')
        data = {"lat": 12.97, "lng": 77.59, "radius_km": 5}
        response = api_client.post(url, data)
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data.get('drivers', [])) >= 0

    def test_ride_history_success(self, authenticated_rider_client, rider_user, ride):
        ride.rider = rider_user
        ride.status = Ride.Status.COMPLETED
        ride.save()
        
        url = reverse('ride-history')
        response = authenticated_rider_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 1

    def test_fare_config_view(self, authenticated_rider_client):
        url = "/api/rides/fare-config/"
        
        # Test full list
        response = authenticated_rider_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        
        # Test specific type
        response = authenticated_rider_client.get(url, {'type': 'go'})
        assert response.status_code == status.HTTP_200_OK
        assert response.data['vehicle_type'] == 'go'
