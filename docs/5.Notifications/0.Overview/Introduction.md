# Introduction to the Notifications Module

The Notifications module is a critical layer of the Uber Clone platform, providing real-time visibility into system events for all users.

## Global Objectives

1. **Reliable Delivery**: Ensure that critical ride updates (e.g.,"Driver Arrived") hit the user's device within seconds.
2. **Multi-Channel Reach**: Provide a unified interface for sending Push, SMS, and Email notifications without the caller needing to know the low-level provider details.
3. **User Preference**: Respect the user's choices regarding which channels they want to receive specific notifications through (e.g., Email for receipts, Push for ride status).
4. **Resilience**: Implement automated retries and dead-letter queues to handle transient network issues and provider downtime.

## Technical Stack

- **Backend**: Python, Django, Django REST Framework.
- **Messaging**: Celery with Redis broker for asynchronous delivery tasks.
- **Providers**: 
- **Push**: Expo Push (for mobile apps).
- **Email**: SendGrid / SMTP (for receipts and welcome emails).
- **SMS**: Twilio / AWS SNS (for OTPs and critical alerts).
- **Real-time BROADCAST**: Django Channels (WebSockets) for in-app live updates.

## The Notification Concept

A `Notification` is a persistent record that tracks an event's journey from `PENDING` to `SENT` or `FAILED`. Every core business event (e.g., ride creation, payment completion, document approval) triggers a notification dispatch through the central **Notification Service**.
