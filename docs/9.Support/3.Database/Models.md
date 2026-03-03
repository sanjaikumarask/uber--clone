# Database Models: Support Module

The Support system relies on three primary models to represent both reactive assistance requests and real-time safety alerts.

## The `SupportTicket` Model

The transactional entity for standard inquiries and disputes.

### Key Fields
- `ride`: The historical context (linked to the `Ride` model).
- `user`: The reporter (Rider or Driver).
- `reason`: `OVERCHARGED`, `DRIVER_MISCONDUCT`, `ROUTE_DEVIATION`, `OTHER`.
- `status`: `OPEN`, `RESOLVED`, `REJECTED`.
- `resolved_by`: The Admin User who handled the request.
- `resolution_note`: Detailed text explaining the platform's action.

## `Emergency` Model (SOS Alerts)

Designed specifically for real-time safety signaling.

### Key Fields
- `ride`: The connection to the live journey.
- `user`: The person who triggered the SOS.
- `lat / lng`: A static"Snapshot"of where the user was when they hit the button.
- `status`: `ACTIVE`, `RESOLVED`, `FALSE_ALARM`.

The `lat` and `lng` fields are critical for safety, as they provide a permanent record of the location even if the driver's GPS is subsequently lost.

## `FAQ` Model

The knowledge base for self-service help.

### Categorization
- `audience`: `RIDER`, `DRIVER`, `BOTH`.
- `category`: `PAYMENT`, `RIDE_ISSUE`, `ACCOUNT`, `SAFETY`.
- `is_active`: Allows admins to draft content without publishing it immediately.
