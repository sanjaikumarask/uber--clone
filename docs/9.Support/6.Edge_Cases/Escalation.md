# Edge Cases: Escalation & Unresolved Support

The Escalation and Safety Management system handles constraints on promotional campaigns, ensuring they remain financially sustainable and consistent for all riders.

## The Problem: Unresolved Issues & False Alarms

In a high-intensity marketplace, a support request or safety alert can"break"or be"misused"in several ways:
- **Unresponsive Support**: A ticket remains `OPEN` for more than 48 hours without an admin response.
- **False SOS Alarms**: A driver or rider accidentally hits the SOS button.
- **High-Priority Safety Risks**: Misconduct or safety threats that require immediate intervention and account suspension.

## Recovery Layer 1: SLA Monitoring (Escalation)

The system can be configured to monitor `SupportTicket` timeliness:
- **Escalation Trigger**: A background task identifies tickets that have been `OPEN` for $> 48$ hours.
- **Action**: `is_escalated = True` is set, and the ticket is moved to a"High Priority"queue for immediate admin review.

## Recovery Layer 2: False Alarm Dismissal (SOS)

For SOS alerts:
- **`FALSE_ALARM` Status**: Admins can quickly mark an emergency as `FALSE_ALARM` to dismiss it from the dashboard while still maintaining a persistent record.
- **Verification Protocol**: Admins are encouraged to call the driver and rider before dismissing an SOS alert.

## The User Experience (In-App Feedback)

While of a support escalation:
- **Escalated Badge**: The rider app shows"Escalated for Priority Review"on the ticket dashboard.
- **Emergency Alert**: Riders are informed of the SOS's `RESOLVED` status via an in-app banner for safety.

## Atomic Transactions (Reliability)

Every set of related status updates and administrative notes is wrapped in a **Postgres Transaction** (`transaction.atomic()`). This ensures that the state changes are only committed alongside the audit record.
