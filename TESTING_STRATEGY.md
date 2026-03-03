# Uber Backend Testing Strategy

## 1. Overview
This document outlines the testing architecture for the Uber-clone backend. We use a pyramid approach: high volume of Unit Tests, medium volume of Integration Tests, and focused End-to-End (E2E) flows.

## 2. Tools & Frameworks
- **Primary Framework**: `pytest`
- **Django Integration**: `pytest-django`
- **Mocking**: `unittest.mock` and `mocker`
- **API Testing**: `rest_framework.test.APIClient`
- **Performance**: `Locust`
- **Code Coverage**: `pytest-cov`

## 3. Test Categories

### A. Unit Tests
- **Locations**: `apps/<app_name>/tests/test_units.py`
- **Focus**: Pure logic (fare calculation engines, distance formulas, promo code validation).
- **Mocks**: No database, no network.

### B. Integration Tests (API & DB)
- **Locations**: `apps/<app_name>/tests/test_api.py`
- **Focus**: Request/Response lifecycle, Database persistence, Signal triggers.
- **Scenarios**:
- Ride Request Flow
- Payment Processing & Idempotency
- Ledger Reconciliation logic

### C. Async & Task Tests (Celery)
- **Focus**: Task reliability, retries, and background state changes.
- **Approach**: Use `celery_app.conf.task_always_eager = True` for integration or manual task execution for unit testing.

### D. Performance Tests
- **Focus**: Throughput, Latency under load, Race condition detection (Matching engine).

## 4. Critical Paths to Cover
1. **Ride Matching Engine**: Sorting logic, skip locked, concurrency.
2. **Financial Integrity**: Ledger credit/debit, Triple-entry reconciliation alerts.
3. **Idempotency**: Preventing duplicate payments and duplicate ride requests.
4. **Adaptive Shedding**: System behavior under high load simulations.

## 5. Execution
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=.

# Run specific app
pytest apps/rides/tests/
```
