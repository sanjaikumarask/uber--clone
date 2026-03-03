# Uber Clone - Full Project Setup & Documentation

This document provides a comprehensive guide for setting up and running all modules of the Uber Clone project, including the Backend, Mobile Apps, and Web Dashboards.

---

## Project Architecture
- **Backend**: Django REST Framework (DRF), WebSockets (Channels), PostgreSQL, Redis, Kafka, Celery.
- **Rider Web**: React + Vite + TypeScript (Dashboard/Booking).
- **Rider App**: Expo / React Native (Mobile Booking).
- **Driver App**: Expo / React Native (Fleet/Dispatch).
- **Admin Dashboard**: React + Vite + TypeScript (Live Monitoring/Audit).

---

## Docker Infrastructure

The entire backend and infrastructure are containerized.

### Backend Services
|Container|Role|
|:---|:---|
|`uber_postgres`|PostgreSQL Database (Source of Truth)|
|`uber_redis`|Cache, Celery Broker, GeoIndex for Driver Matching|
|`uber_kafka`|Message Broker for Async Event Streaming|
|`uber_backend`|Django Web Server (Daphne/ASGI)|
|`uber_celery`|Background Task Processing (Matching/Payouts)|
|`uber_celery_beat`|Periodic Tasks (Audits/Scheduler)|
|`uber_nginx`|Reverse Proxy for Static Files & Routing|

### Common Docker Commands
```bash
# Start all services in the background
docker compose up -d

# Stop all services
docker compose down

# View logs for a specific service
docker logs -f uber_backend
docker logs -f uber_celery

# Run database migrations
docker exec uber_backend python manage.py migrate

# Access Django Shell
docker exec -it uber_backend python manage.py shell

# Interactive terminal inside backend
docker exec -it uber_backend bash
```

---

## Backend Module (Django)

### Core Dependencies
- `Django`: Web Framework
- `channels`: Real-time WebSockets
- `celery`: Async Task Queue
- `kafka-python`: Event Streaming
- `razorpay`: Payment Integration
- `exponent-server-sdk`: Push Notifications
- `django-prometheus`: APM & Metrics

### Setup Instructions
1. **Environment**: Create a `.env` file in the root directory (refer to `.env.example`).
2. **Infrastructure**: Ensure Docker is running.
3. **Initial Schema**:
```bash
docker exec uber_backend python manage.py migrate
```
4. **Admin User**:
```bash
docker exec -it uber_backend python manage.py createsuperuser
```

---

## Mobile Apps (Rider & Driver)

Both apps use **Expo** (React Native).

### Core Dependencies
- `react-native-maps`: Location visualization
- `expo-location`: Real-time GPS tracking
- `@react-navigation/stack`: App routing
- `axios`: API Communication
- `react-native-razorpay`: Payments (Rider App)
- `zustand`: State Management

### Startup Commands
```bash
# Navigate to the app directory
cd frontend/rider-app # or frontend/driver-app

# Install dependencies
npm install

# Start the Expo Dev Server
npx expo start
```

---

## Web Dashboards (Admin & Rider Web)

Built with **Vite + React + TypeScript**.

### Core Dependencies
- `@react-google-maps/api`: Interactive Maps
- `recharts`: Analytics & Earnings graphs
- `react-router-dom`: SPA routing
- `zustand`: State Management

### Startup Commands
```bash
# Navigate to the dashboard directory
cd admin-dashboard # or frontend/rider-web

# Install dependencies
npm install

# Start Development Server
npm run dev

# Build for Production
npm run build
```

---

## Testing & Quality Assurance

### API Integration Tests
A comprehensive E2E script is provided to verify the full ride lifecycle.
```bash
# Inside the backend container
bash /app/test_full_flow.sh
```

### Unit Tests
```bash
# Run pytest for the entire backend
docker exec uber_backend pytest
```

---

## System Monitoring
- **Prometheus Metrics**: `http://localhost:8000/metrics`
- **Flower (Celery Monitor)**: `http://localhost:5555`
- **Admin Dashboard**: `http://localhost/admin` (via Nginx)
