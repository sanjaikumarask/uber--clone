import random
from locust import HttpUser, task, between

class UberRiderUser(HttpUser):
    wait_time = between(1, 5)
    token = None

    def on_start(self):
        """Log in and get JWT token"""
        # Note: This assumes a pre-existing test user or a simple auth flow.
        # In a real setup, we might hit the /api/auth/login endpoint.
        username = f"rider_{random.randint(1, 1000)}"
        # For simulation, we assume basic auth or a bypass for stress testing.
        # Here we just set a header placeholder.
        self.auth_header = {"Authorization": "Bearer mock-token-for-load-test"}

    @task(3)
    def estimate_fare(self):
        self.client.post("/api/rides/estimate-fare/", json={
            "pickup_lat": 13.0827 + (random.random() * 0.01),
            "pickup_lng": 80.2707 + (random.random() * 0.01),
            "drop_lat": 13.0569 + (random.random() * 0.01),
            "drop_lng": 80.2425 + (random.random() * 0.01)
        }, headers=self.auth_header)

    @task(1)
    def book_ride(self):
        # Unique idempotency key per request
        headers = self.auth_header.copy()
        headers["X-Idempotency-Key"] = f"load-test-{random.random()}"
        
        self.client.post("/api/rides/request/", json={
            "pickup_lat": 13.0827,
            "pickup_lng": 80.2707,
            "drop_lat": 13.0569,
            "drop_lng": 80.2425,
            "vehicle_type": "go"
        }, headers=headers)

class UberDriverUser(HttpUser):
    wait_time = between(2, 4)
    auth_header = {"Authorization": "Bearer mock-token-for-driver"}

    @task
    def update_location(self):
        # Drivers constantly update their location in Redis
        # Note: This might hit a WebSocket or a separate API
        self.client.post("/api/drivers/update-location/", json={
            "lat": 13.0827 + (random.random() * 0.05),
            "lng": 80.2707 + (random.random() * 0.05)
        }, headers=self.auth_header)
