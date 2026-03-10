import json
import pytest
import uuid
import time
from unittest.mock import patch, MagicMock
from django.db import DatabaseError
from apps.rides.models import Ride
from apps.drivers.models import Driver
from django.contrib.auth import get_user_model
from consumers.ride_events import main, process_ride_event, match_and_assign_driver, send_to_dlq

User = get_user_model()

@pytest.mark.django_db
class TestRideEventsFinal:

    def create_test_user(self, role="rider"):
        uid = uuid.uuid4().hex[:8]
        username = f"user_{uid}"
        phone = f"5{uuid.uuid4().hex[:9]}" 
        return User.objects.create_user(username=username, role=role, phone=phone[:10])

    @pytest.fixture
    def setup_data(self):
        rider = self.create_test_user(role="rider")
        driver_user = self.create_test_user(role="driver")
        driver, _ = Driver.objects.get_or_create(user=driver_user)
        driver.status = Driver.Status.ONLINE
        driver.save()
        
        ride = Ride.objects.create(
            rider=rider, 
            driver=driver,
            status=Ride.Status.ONGOING, 
            pickup_lat=0, pickup_lng=0, drop_lat=0, drop_lng=0,
            final_fare=100.0,
            search_attempt=0
        )
        return rider, driver, ride

    @patch('consumers.ride_events.KafkaConsumer')
    @patch('consumers.ride_events.process_ride_event')
    def test_main_loop_and_consumer_init(self, mock_process, mock_consumer_class):
        mock_consumer = MagicMock()
        mock_consumer_class.return_value = mock_consumer
        message = MagicMock()
        message.value = {"event": "COMPLETED", "ride_id": 1}
        mock_consumer.__iter__.return_value = [message]
        
        with patch('time.sleep', side_effect=[None, Exception("Stop loop")]):
            try:
                main()
            except Exception as e:
                if "Stop loop" not in str(e): raise
        
        mock_consumer_class.assert_called_once()
        mock_process.assert_called_once_with(message.value)

    @patch('consumers.ride_events.update_ride_status')
    def test_process_ride_completed(self, mock_update, setup_data):
        rider, driver, ride = setup_data
        event = {"event": Ride.Status.COMPLETED, "ride_id": ride.id}
        process_ride_event(event)
        mock_update.assert_called()

    @patch('consumers.ride_events.update_ride_status')
    def test_process_ride_cancelled(self, mock_update, setup_data):
        rider, driver, ride = setup_data
        ride.status = Ride.Status.SEARCHING
        ride.save()
        event = {"event": Ride.Status.CANCELLED, "ride_id": ride.id}
        process_ride_event(event)
        mock_update.assert_called()

    @patch('consumers.ride_events.update_ride_status')
    def test_process_ride_accepted(self, mock_update, setup_data):
        rider, driver, ride = setup_data
        ride.status = Ride.Status.OFFERED
        ride.save()
        event = {"event": "ACCEPTED", "ride_id": ride.id}
        process_ride_event(event)
        mock_update.assert_called()

    @patch('consumers.ride_events.KafkaConsumer')
    @patch('consumers.ride_events.send_to_dlq')
    @patch('time.sleep', return_value=None)
    def test_malformed_json_to_dlq(self, mock_sleep, mock_dlq, mock_consumer_class):
        mock_consumer = MagicMock()
        mock_consumer_class.return_value = mock_consumer
        message = MagicMock()
        message.value = {"_error": "MALFORMED", "raw": "bad-data"}
        mock_consumer.__iter__.return_value = [message]
        
        with patch('consumers.ride_events.NoBrokersAvailable', side_effect=[None, Exception("Stop")]):
             try:
                 main()
             except Exception:
                 pass
        mock_dlq.assert_called_with(message.value, "Malformed JSON")

    @patch('consumers.ride_events.KafkaConsumer')
    @patch('consumers.ride_events.process_ride_event')
    @patch('consumers.ride_events.send_to_dlq')
    @patch('time.sleep', return_value=None)
    def test_database_unavailable_retry(self, mock_sleep, mock_dlq, mock_process, mock_consumer_class, setup_data):
        mock_consumer = MagicMock()
        mock_consumer_class.return_value = mock_consumer
        message = MagicMock()
        message.value = {"event": "COMPLETED", "ride_id": setup_data[2].id}
        mock_consumer.__iter__.return_value = [message]
        mock_process.side_effect = DatabaseError("DB Down")
        
        with patch('consumers.ride_events.NoBrokersAvailable', side_effect=[None, Exception("Stop loop")]):
            try:
                main()
            except Exception:
                pass
        mock_dlq.assert_called()

    @patch('consumers.ride_events.KafkaConsumer')
    @patch('consumers.ride_events.process_ride_event')
    @patch('consumers.ride_events.send_to_dlq')
    @patch('apps.notifications.services.alerts.send_critical_alert')
    @patch('time.sleep', return_value=None)
    def test_max_retries_exceeded_dlq_alert(self, mock_sleep, mock_alert, mock_dlq, mock_process, mock_consumer_class, setup_data):
        mock_consumer = MagicMock()
        mock_consumer_class.return_value = mock_consumer
        message = MagicMock()
        message.value = {"event": "COMPLETED", "ride_id": setup_data[2].id, "_retries": 3}
        mock_consumer.__iter__.return_value = [message]
        mock_process.side_effect = Exception("Permanent failure")
        
        with patch('consumers.ride_events.NoBrokersAvailable', side_effect=[None, Exception("Stop loop")]):
             try:
                 main()
             except Exception:
                 pass
        mock_dlq.assert_called_with(message.value, "Max retries exceeded: Permanent failure")
        mock_alert.assert_called_once()

    def test_unknown_event_type_handled(self, setup_data):
        rider, driver, ride = setup_data
        event = {"event": "FLY_MODE", "ride_id": ride.id}
        with patch('consumers.ride_events.logger') as mock_logger:
            process_ride_event(event)
            mock_logger.warning.assert_called_with("Unknown event type: FLY_MODE")

    @patch('consumers.ride_events.KafkaConsumer')
    def test_kafka_conn_retry(self, mock_consumer_class):
         from kafka.errors import NoBrokersAvailable
         mock_consumer_class.side_effect = [NoBrokersAvailable(), MagicMock()]
         with patch('time.sleep', side_effect=[None, Exception("Stop loop")]):
             try:
                 main()
             except Exception:
                 pass
         assert mock_consumer_class.call_count == 2

    @patch('consumers.ride_events.update_ride_status')
    def test_process_ride_searching(self, mock_update, setup_data):
        rider, driver, ride = setup_data
        ride.status = Ride.Status.SEARCHING
        ride.save()
        event = {
            "event": "RIDE_SEARCHING", 
            "ride_id": ride.id, 
            "driver_ids": [driver.id],
            "attempt": 1
        }
        process_ride_event(event)
        mock_update.assert_called()
        
    def test_safe_deserialize_error(self):
        from consumers.ride_events import safe_deserialize
        res = safe_deserialize(b" { invalid json } ")
        assert res["_error"] == "MALFORMED"
        assert "raw" in res

    # --- Edge Cases for higher coverage ---
    def test_match_and_assign_driver_invalid_event(self):
        with patch('consumers.ride_events.logger') as mock_logger:
            match_and_assign_driver({"ride_id": 1}) # missing attempt/drivers
            mock_logger.warning.assert_called()

    def test_match_and_assign_driver_not_found(self):
        with patch('consumers.ride_events.logger') as mock_logger:
            match_and_assign_driver({"ride_id": 9999, "driver_ids": [1], "attempt": 1})
            mock_logger.error.assert_called_with("Ride 9999 not found")

    def test_match_and_assign_driver_stale_or_wrong_status(self, setup_data):
        rider, driver, ride = setup_data
        ride.status = Ride.Status.SEARCHING
        ride.search_attempt = 5
        ride.save()
        
        with patch('consumers.ride_events.logger') as mock_logger:
            # Stale attempt
            match_and_assign_driver({"ride_id": ride.id, "driver_ids": [driver.id], "attempt": 5})
            mock_logger.info.assert_called_with(f"Stale matching event for ride {ride.id}")
            
            # Wrong status
            ride.status = Ride.Status.ONGOING
            ride.search_attempt = 0
            ride.save()
            match_and_assign_driver({"ride_id": ride.id, "driver_ids": [driver.id], "attempt": 1})
            mock_logger.info.assert_called_with(f"Ride {ride.id} not SEARCHING")

    def test_match_and_assign_driver_no_available(self, setup_data):
        rider, driver, ride = setup_data
        ride.status = Ride.Status.SEARCHING
        ride.save()
        driver.status = Driver.Status.OFFLINE
        driver.save()
        
        with patch('consumers.ride_events.logger') as mock_logger:
            match_and_assign_driver({"ride_id": ride.id, "driver_ids": [driver.id], "attempt": 1})
            mock_logger.info.assert_called_with(f"No available drivers for ride {ride.id}")

    def test_process_ride_event_missing_fields(self):
        with patch('consumers.ride_events.logger') as mock_logger:
            process_ride_event({"event": "TEST"}) # missing ride_id
            mock_logger.error.assert_called_with("Event missing type or ride_id")

    @patch('consumers.ride_events.update_ride_status')
    def test_process_ride_event_ongoing_requested(self, mock_update, setup_data):
        rider, driver, ride = setup_data
        # ONGOING
        process_ride_event({"event": Ride.Status.ONGOING, "ride_id": ride.id})
        # REQUESTED
        process_ride_event({"event": "REQUESTED", "ride_id": ride.id})
        assert mock_update.call_count == 2

    @patch('consumers.ride_events.get_kafka_producer', return_value=None)
    def test_send_to_dlq_no_producer(self, mock_get):
        with patch('consumers.ride_events.logger') as mock_logger:
            send_to_dlq({"ride_id": 1}, "reason")
            mock_logger.critical.assert_called()

    @patch('consumers.ride_events.KafkaProducer')
    def test_send_to_dlq_exception(self, mock_producer_class):
        mock_p = MagicMock()
        mock_producer_class.return_value = mock_p
        mock_p.send.side_effect = Exception("Kafka down")
        with patch('consumers.ride_events.get_kafka_producer', return_value=mock_p):
            with patch('consumers.ride_events.logger') as mock_logger:
                send_to_dlq({"ride_id": 1}, "reason")
                mock_logger.critical.assert_called()
                
    def test_get_kafka_producer_exception(self):
        with patch('consumers.ride_events.KafkaProducer', side_effect=Exception("Failed")):
            from consumers.ride_events import get_kafka_producer
            assert get_kafka_producer() is None
