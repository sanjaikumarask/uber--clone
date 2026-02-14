# 🧪 Testing Guide - Uber Clone Backend

## 📋 **Overview**

This guide covers unit testing and integration testing for the Uber Clone backend using pytest and Django's testing framework.

---

## 🎯 **Testing Strategy**

### **Test Types:**

1. **Unit Tests** - Test individual functions and methods in isolation
2. **Integration Tests** - Test API endpoints and interactions between components
3. **End-to-End Tests** - Test complete user workflows

### **Coverage Goals:**
- **Minimum:** 70% code coverage
- **Target:** 85% code coverage
- **Critical paths:** 100% coverage (auth, payments, ride lifecycle)

---

## 🚀 **Quick Start**

### **1. Install Test Dependencies:**
```bash
cd backend
docker exec uber_backend pip install -r requirements-test.txt
```

### **2. Run All Tests:**
```bash
docker exec uber_backend pytest
```

### **3. Run with Coverage:**
```bash
docker exec uber_backend pytest --cov=apps --cov-report=html
```

### **4. View Coverage Report:**
```bash
# Coverage report will be in backend/htmlcov/index.html
# Open in browser to see detailed coverage
```

---

## 📁 **Test Structure**

```
backend/
├── apps/
│   ├── users/
│   │   └── tests/
│   │       ├── __init__.py
│   │       └── test_auth.py          # User authentication tests
│   ├── drivers/
│   │   └── tests/
│   │       ├── __init__.py
│   │       └── test_drivers.py       # Driver functionality tests
│   ├── rides/
│   │   └── tests/
│   │       ├── __init__.py
│   │       ├── test_models.py        # Ride model tests
│   │       ├── test_api.py           # Ride API tests
│   │       ├── test_ride_e2e.py      # End-to-end ride tests
│   │       └── test_smoke.py         # Basic smoke tests
│   ├── payments/
│   │   └── tests/
│   │       └── test_payment_flow.py  # Payment tests
│   └── notifications/
│       └── tests.py                   # Notification tests
├── conftest.py                        # Pytest fixtures
└── pytest.ini                         # Pytest configuration
```

---

## 🧪 **Running Tests**

### **Run All Tests:**
```bash
docker exec uber_backend pytest
```

### **Run Specific Test File:**
```bash
docker exec uber_backend pytest apps/users/tests/test_auth.py
```

### **Run Specific Test Class:**
```bash
docker exec uber_backend pytest apps/users/tests/test_auth.py::TestUserLogin
```

### **Run Specific Test:**
```bash
docker exec uber_backend pytest apps/users/tests/test_auth.py::TestUserLogin::test_rider_login_success
```

### **Run Tests by Marker:**
```bash
# Run only unit tests
docker exec uber_backend pytest -m unit

# Run only integration tests
docker exec uber_backend pytest -m integration

# Run only e2e tests
docker exec uber_backend pytest -m e2e

# Skip slow tests
docker exec uber_backend pytest -m "not slow"
```

### **Run with Verbose Output:**
```bash
docker exec uber_backend pytest -v
```

### **Run with Print Statements:**
```bash
docker exec uber_backend pytest -s
```

### **Stop on First Failure:**
```bash
docker exec uber_backend pytest -x
```

### **Run Last Failed Tests:**
```bash
docker exec uber_backend pytest --lf
```

---

## 📊 **Coverage Reports**

### **Generate Coverage Report:**
```bash
docker exec uber_backend pytest --cov=apps --cov-report=html --cov-report=term
```

### **Coverage Report Types:**

1. **Terminal Report:**
   ```bash
   docker exec uber_backend pytest --cov=apps --cov-report=term-missing
   ```
   Shows coverage with line numbers of missing coverage

2. **HTML Report:**
   ```bash
   docker exec uber_backend pytest --cov=apps --cov-report=html
   ```
   Generates `htmlcov/index.html` - open in browser

3. **XML Report (for CI/CD):**
   ```bash
   docker exec uber_backend pytest --cov=apps --cov-report=xml
   ```

### **View Coverage:**
```bash
# Copy HTML report from container
docker cp uber_backend:/app/htmlcov ./backend/htmlcov

# Open in browser
firefox backend/htmlcov/index.html
# or
google-chrome backend/htmlcov/index.html
```

---

## ✅ **Test Examples**

### **Unit Test Example:**
```python
import pytest
from apps.rides.services.fare_calculator import calculate_fare

@pytest.mark.unit
def test_fare_calculation():
    """Test basic fare calculation"""
    fare = calculate_fare(distance=5.0, duration=15)
    assert fare > 0
    assert isinstance(fare, Decimal)
```

### **Integration Test Example:**
```python
import pytest
from rest_framework.test import APIClient

@pytest.mark.django_db
@pytest.mark.integration
def test_create_ride(authenticated_rider_client):
    """Test ride creation via API"""
    data = {
        "pickup_lat": 13.0827,
        "pickup_lng": 80.2707,
        "dropoff_lat": 13.0569,
        "dropoff_lng": 80.2425
    }
    
    response = authenticated_rider_client.post(
        "/api/rides/create/",
        data,
        format="json"
    )
    
    assert response.status_code == 201
    assert "ride_id" in response.data
```

### **End-to-End Test Example:**
```python
import pytest

@pytest.mark.django_db
@pytest.mark.e2e
def test_complete_ride_flow(rider_user, driver_user, api_client):
    """Test complete ride lifecycle"""
    # 1. Rider books ride
    api_client.force_authenticate(user=rider_user)
    response = api_client.post("/api/rides/create/", {...})
    ride_id = response.data["ride_id"]
    
    # 2. Driver accepts
    api_client.force_authenticate(user=driver_user)
    api_client.post(f"/api/rides/{ride_id}/accept/")
    
    # 3. Driver arrives
    api_client.post(f"/api/rides/{ride_id}/arrive/")
    
    # 4. Start ride
    api_client.post(f"/api/rides/{ride_id}/start/")
    
    # 5. Complete ride
    api_client.post(f"/api/rides/{ride_id}/complete/")
    
    # Verify final state
    ride = Ride.objects.get(id=ride_id)
    assert ride.status == Ride.Status.COMPLETED
```

---

## 🔧 **Using Fixtures**

### **Available Fixtures:**

```python
# In your tests, use these fixtures:

def test_something(api_client):
    """Use API client"""
    pass

def test_with_rider(rider_user):
    """Use pre-created rider"""
    pass

def test_with_driver(driver_user):
    """Use pre-created driver"""
    pass

def test_authenticated(authenticated_rider_client):
    """Use authenticated client"""
    pass

def test_with_ride(sample_ride):
    """Use pre-created ride"""
    pass

def test_with_mocks(mock_google_maps):
    """Use mocked Google Maps"""
    pass
```

### **Creating Custom Fixtures:**
```python
# In conftest.py or test file

@pytest.fixture
def completed_ride(db, rider_user, driver_user):
    """Fixture for completed ride"""
    from apps.rides.models import Ride
    
    driver = Driver.objects.get(user=driver_user)
    
    return Ride.objects.create(
        rider=rider_user,
        driver=driver,
        status=Ride.Status.COMPLETED,
        final_fare=Decimal("150.00")
    )
```

---

## 🎯 **Test Coverage by Module**

### **Users App:**
- ✅ User registration (rider, driver, admin)
- ✅ User login (phone + password)
- ✅ JWT token generation
- ✅ Profile management
- ✅ Password validation
- ✅ Duplicate phone number handling

### **Rides App:**
- ✅ Ride creation
- ✅ Ride status transitions
- ✅ OTP generation and verification
- ✅ Fare calculation
- ✅ Ride cancellation
- ✅ Ride history
- ✅ Active ride retrieval

### **Drivers App:**
- ✅ Driver profile creation
- ✅ Status management (online/offline)
- ✅ Location tracking
- ✅ Ride acceptance/rejection
- ✅ Earnings calculation
- ✅ Statistics

### **Payments App:**
- ✅ Payment processing
- ✅ Payment verification
- ✅ Refund handling
- ✅ Payment history

---

## 🐛 **Debugging Tests**

### **Use pdb Debugger:**
```python
def test_something():
    import pdb; pdb.set_trace()
    # Test code here
```

### **Print Debugging:**
```bash
# Run with -s to see print statements
docker exec uber_backend pytest -s
```

### **Verbose Output:**
```bash
docker exec uber_backend pytest -vv
```

### **Show Local Variables on Failure:**
```bash
docker exec uber_backend pytest -l
```

---

## 📈 **Continuous Integration**

### **GitHub Actions Example:**
```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v2
      
      - name: Build containers
        run: docker-compose up -d
      
      - name: Run tests
        run: docker exec uber_backend pytest --cov=apps --cov-report=xml
      
      - name: Upload coverage
        uses: codecov/codecov-action@v2
        with:
          file: ./backend/coverage.xml
```

---

## ✅ **Best Practices**

### **1. Test Naming:**
```python
# Good
def test_rider_can_book_ride():
    pass

def test_driver_cannot_accept_assigned_ride():
    pass

# Bad
def test1():
    pass

def test_stuff():
    pass
```

### **2. Arrange-Act-Assert Pattern:**
```python
def test_create_ride():
    # Arrange
    rider = create_rider()
    data = {"pickup_lat": 13.08, ...}
    
    # Act
    response = client.post("/api/rides/", data)
    
    # Assert
    assert response.status_code == 201
    assert Ride.objects.count() == 1
```

### **3. Use Fixtures for Setup:**
```python
# Good
def test_with_fixture(sample_ride):
    assert sample_ride.status == Ride.Status.PENDING

# Bad
def test_without_fixture():
    rider = User.objects.create(...)
    ride = Ride.objects.create(...)
    assert ride.status == Ride.Status.PENDING
```

### **4. Test One Thing:**
```python
# Good
def test_ride_creation():
    # Only test creation
    pass

def test_ride_status_update():
    # Only test status update
    pass

# Bad
def test_ride_everything():
    # Tests creation, update, delete, etc.
    pass
```

### **5. Mock External Services:**
```python
@patch('apps.rides.services.google_maps.get_route')
def test_ride_with_mocked_maps(mock_get_route):
    mock_get_route.return_value = {"distance": 5.2}
    # Test code
```

---

## 🚀 **Quick Commands Reference**

```bash
# Run all tests
docker exec uber_backend pytest

# Run with coverage
docker exec uber_backend pytest --cov=apps

# Run specific app tests
docker exec uber_backend pytest apps/rides/tests/

# Run and stop on first failure
docker exec uber_backend pytest -x

# Run last failed tests
docker exec uber_backend pytest --lf

# Run verbose
docker exec uber_backend pytest -v

# Run with print statements
docker exec uber_backend pytest -s

# Generate HTML coverage report
docker exec uber_backend pytest --cov=apps --cov-report=html

# Run only fast tests
docker exec uber_backend pytest -m "not slow"
```

---

## 📊 **Current Test Coverage**

Run this to see current coverage:
```bash
docker exec uber_backend pytest --cov=apps --cov-report=term-missing
```

**Target Coverage:**
- **Users:** 85%+
- **Rides:** 90%+
- **Drivers:** 85%+
- **Payments:** 80%+
- **Overall:** 85%+

---

## 🎯 **Next Steps**

1. **Install test dependencies:**
   ```bash
   docker exec uber_backend pip install -r requirements-test.txt
   ```

2. **Run initial tests:**
   ```bash
   docker exec uber_backend pytest
   ```

3. **Check coverage:**
   ```bash
   docker exec uber_backend pytest --cov=apps --cov-report=html
   ```

4. **View coverage report:**
   ```bash
   docker cp uber_backend:/app/htmlcov ./backend/htmlcov
   firefox backend/htmlcov/index.html
   ```

5. **Add more tests** as needed for uncovered code

---

## 🎉 **You're Ready to Test!**

Your backend now has comprehensive test coverage for:
- ✅ User authentication and authorization
- ✅ Ride creation and management
- ✅ Driver functionality
- ✅ API endpoints
- ✅ Business logic

**Start testing with:**
```bash
docker exec uber_backend pytest -v
```

Happy testing! 🧪🚀
