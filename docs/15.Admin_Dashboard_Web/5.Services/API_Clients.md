# Services & API Clients: Admin Dashboard Web

The Admin Dashboard communicates with the backend via two channels: a REST API (Axios) for data CRUD operations, and a native WebSocket for real-time live map and alert streaming.

## The Service Architecture

All services are grouped under `src/services/` and are thin wrappers over an Axios instance or WebSocket client. Business logic lives in React components or custom hooks — not in the services layer.

## Axios Configuration

```typescript
// src/services/apiClient.ts
const api = axios.create({baseURL: import.meta.env.VITE_API_URL});

// Request interceptor: inject JWT
api.interceptors.request.use(config => {
const token = localStorage.getItem('admin_token');
if (token) config.headers.Authorization = `Bearer ${token}`;
return config;
});

// Response interceptor: redirect on 401/403
api.interceptors.response.use(
r => r,
err => {if (err.response?.status === 401) window.location.href ='/login';}
);
```

## Service Modules

### `authService`
- `login(email, password)` → Fetches and stores admin JWT.
- `logout()` → Clears token and redirects to `/login`.

### `ridesService`
- `list(params)` → Paginated ride history.
- `get(id)` → Full ride audit detail.
- `forceCancel(id, reason)` → Admin-initiated cancellation.

### `driversService`
- `list(params)` → Full driver roster.
- `get(id)` → Driver profile with stats and documents.
- `setStatus(id, status)` → Block / Unblock driver.
- `approveDocument(docId)` / `rejectDocument(docId, reason)` → Verification queue actions.

### `paymentsService`
- `listTransactions(params)`, `listLedger(params)`, `listPayouts(params)`.
- `triggerRefund(paymentId, amount)` → Initiates a partial or full refund.
- `processPayout(payoutId)` → Triggers backend payout task.

### `offersService` / `incentivesService`
- Full CRUD: `list`, `create`, `update`, `deactivate`.

### `supportService`
- `listTickets(params)`, `resolveTicket(id, note)`, `rejectTicket(id, note)`.
- `listEmergencies(params)`, `resolveEmergency(id, note, status)`.

### `analyticsService`
- `getDailyRevenue(range)`, `getRideVolume(range)`, `getDriverStats()`.

### `systemService`
- `getAlerts(params)` → Paginated `SystemLog` entries.
- `getSummary()` → Overview KPI data.

## WebSocket Service

```typescript
// src/services/liveMapSocket.ts
class LiveMapSocket {
connect(onMessage: (event: LiveMapEvent) => void): void;
disconnect(): void;
}
```

- Manages a single `WebSocket` connection to `wss://.../ws/admin_live_map/`.
- Dispatches incoming events (`driver.location.update`, `emergency.sos.alert`, `ride.booking.alert`) to the provided `onMessage` callback.
- Implements automatic exponential-backoff reconnection on disconnect.
