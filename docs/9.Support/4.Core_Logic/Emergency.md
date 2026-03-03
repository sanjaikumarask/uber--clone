# Emergency (SOS) System Logic

The Emergency (SOS) system is the high-priority safety layer of the Uber Clone, specifically designed to capture and broadcast critical safety alerts during active rides.

## The Emergency Signaling Sequence

1. **Trigger Stage (`POST /api/support/emergency/sos/`)**
- **Ping Capture**: The mobile app instantly captures its current (lat, lng) coordinates.
- **Context Link**: The request includes the `ride_id` to provide immediate driver/rider context.
- **Creation**: An `Emergency` record is created (`status: ACTIVE`).
2. **Broadcaster Stage**: 
- The system identifies the active ride and driver.
- An `emergency.alert` event is pushed via **Django Channels** to the `admin_live_map` WebSocket group.
- The Admin Dashboard instantly shows a Red Pulsing Marker on the map for that specific ride.
3. **Terminal State**: 
- **Success**: `status` set to `RESOLVED`. A `resolution_note` is recorded explaining the action.
- **False Alarm**: `status` set to `FALSE_ALARM`. The alert is dismissed from the admin dashboard's active firehose.

## Data Capture & Audit

The Emergency Engine provides high-precision logging of safety events:
- **Static Snapshot**: Captures the exact (Lat, Lng) at the moment the SOS button was pressed, ensuring a location record even if the GPS is subsequently lost.
- **Ride Context**: Instantly links to the [**Rides module**](../../3.Rides/Rides_Readme.md) to provide driver/rider details and current status.
- **Admin Resolution**: Every SOS alert must be manually resolved by a platform administrator to ensure human-in-the-loop oversight for safety events.

## The Admin Experience (Firehose)

Admins can monitor **Active SOS Alerts**:
- **A pulsing red marker** for the ride in an SOS state.
- **A sidebar notification** with the driver/rider IDs and a link to their contact information.
- **Location Tracking**: The system continues to stream the driver's *current* coordinates in addition to the stagnant"SOS Snapshot"for live monitoring.

## False Alarm Management

The `Emergency.resolve(status=FALSE_ALARM)` method allows admins to quickly dismiss accidental or incorrect SOS triggers while still maintaining a persistent record of the event for potential follow-up or policy warnings.
---

## Flow Diagram

```mermaid
sequenceDiagram
participant User as Rider / Driver
participant API as Support API
participant WS as Django Channels
participant AdminUI as Admin Live Map

User->>API: POST /api/support/emergency/sos/
{ride_id, lat, lng}
API->>API: INSERT Emergency (status=ACTIVE)
Capture GPS snapshot
API->>WS: group_send admin_live_map
emergency.sos.alert {ride, lat, lng}
WS-->>AdminUI: RED pulsing marker appears
AdminUI->>API: PATCH /admin/emergencies/{id}/resolve/
{note, status=RESOLVED}
API-->>AdminUI: 200 OK
```
