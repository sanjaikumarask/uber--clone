import pytest
from unittest.mock import patch, MagicMock
from apps.rides.models import Ride
from apps.drivers.models import Driver
from consumers.ride_events import match_and_assign_driver

@pytest.mark.django_db
class TestConsumersRideEvents:
    def test_invalid_event_type(self):
        match_and_assign_driver({"event": "INVALID"})

    def test_missing_fields(self):
        match_and_assign_driver({"event": "RIDE_SEARCHING", "ride_id": 1})

    def test_ride_not_searching(self, rider_user):
        ride = Ride.objects.create(rider=rider_user, status=Ride.Status.OFFERED, search_attempt=1, pickup_lat=0, pickup_lng=0, drop_lat=0, drop_lng=0)
        match_and_assign_driver({
            "event": "RIDE_SEARCHING",
            "ride_id": ride.id,
            "driver_ids": [1],
            "attempt": 2
        })

    def test_stale_event(self, rider_user):
        ride = Ride.objects.create(rider=rider_user, status=Ride.Status.SEARCHING, search_attempt=5, pickup_lat=0, pickup_lng=0, drop_lat=0, drop_lng=0)
        match_and_assign_driver({
            "event": "RIDE_SEARCHING",
            "ride_id": ride.id,
            "driver_ids": [1],
            "attempt": 2
        })

    @patch("consumers.ride_events.driver_accept_timeout.apply_async")
    def test_successful_match(self, mock_apply, rider_user, driver_user):
        driver = driver_user.driver
        driver.status = Driver.Status.ONLINE
        driver.save()
        ride = Ride.objects.create(rider=rider_user, status=Ride.Status.SEARCHING, search_attempt=1, pickup_lat=0, pickup_lng=0, drop_lat=0, drop_lng=0)
        match_and_assign_driver({
            "event": "RIDE_SEARCHING",
            "ride_id": ride.id,
            "driver_ids": [driver.id],
            "attempt": 2
        })
        ride.refresh_from_db()
        assert ride.status == Ride.Status.OFFERED
        assert ride.driver == driver

    def test_no_available_drivers(self, rider_user):
        ride = Ride.objects.create(rider=rider_user, status=Ride.Status.SEARCHING, search_attempt=1, pickup_lat=0, pickup_lng=0, drop_lat=0, drop_lng=0)

        match_and_assign_driver({
            "event": "RIDE_SEARCHING",
            "ride_id": ride.id,
            "driver_ids": [9999], # Non-existent
            "attempt": 2
        })
        ride.refresh_from_db()
        assert ride.status == Ride.Status.SEARCHING

    @patch("consumers.ride_events.KafkaConsumer")
    def test_main_loop(self, mock_kafka):
        # Setup mock behavior to return one message then stop
        mock_consumer_instance = MagicMock()
        mock_message = MagicMock()
        mock_message.value = {"event": "TEST"}
        mock_consumer_instance.__iter__.return_value = [mock_message]
        mock_kafka.return_value = mock_consumer_instance

        from consumers.ride_events import main
        main()
        
        mock_kafka.assert_called_once()
    
    @patch("consumers.ride_events.KafkaConsumer")
    @patch("consumers.ride_events.time.sleep")
    def test_main_nobrokers(self, mock_sleep, mock_kafka):
        from kafka.errors import NoBrokersAvailable
        mock_kafka.side_effect = [NoBrokersAvailable(), MagicMock()]
        
        from consumers.ride_events import main
        main()
        
        assert mock_kafka.call_count == 2
        mock_sleep.assert_called_once_with(5)
