<<<<<<< HEAD
# Uber Clone (Ride-Hailing Platform)

A production-ready, highly-scalable Uber-like platform featuring real-time tracking, driver matching, automated payouts, and multi-app architecture.

---

## Quick Start

Ensure you have **Docker** and **Docker Compose** installed.

```bash
# Clone the repository
git clone <repo-url>
cd uber-backend

# Start the entire infrastructure
docker compose up -d --build

# Run migrations & setup admin
docker exec -it uber_backend python manage.py migrate
docker exec -it uber_backend python manage.py createsuperuser
```

---

## Project Structure

- **`/backend`**: Django Core API, WebSockets, Celery Workers.
- **`/frontend/rider-app`**: Expo-based Rider booking app.
- **`/frontend/driver-app`**: Expo-based Driver fleet app.
- **`/frontend/rider-web`**: Web dashboard for Riders.
- **`/admin-dashboard`**: Unified Command & Control map for Admins.

---

## Documentation

For detailed setup instructions, module-wise dependencies, and common troubleshooting commands, please refer to the **[SETUP_GUIDE.md](./SETUP_GUIDE.md)**.

> [!TIP]
> **New to the project?** Start with the **[Master Project Workflow](./docs/0.Workflow_Master.md)** for a top-down view of the entire operational flow.

---

## Features
- **Real-time Tracking**: Live GPS updates via Django Channels.
- **Algorithmic Matching Engine**: Rankings based on score, trust, and distance.
- **Secure Payments**: Integrated with Razorpay Checkout & Payouts.
- **Financial Audit**: Double-entry ledger system with automated reconciliation.
- **Adaptive Resilience**: Load shedding and circuit breaking for high availability.
- **Observability**: Integrated with Prometheus, Grafana, and Sentry.
=======
# taxi-python
>>>>>>> taxi-python/main
