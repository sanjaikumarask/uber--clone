# 🔍 Full Project Audit Report
**Date:** 2026-02-27

## Summary
Full cross-audit of all backend APIs vs. all frontend clients (rider-app, driver-app, rider-web, admin-dashboard).

---

## 🔴 CRITICAL — Broken Right Now (Will Crash / 404 / 500)

### 1. rider-web `OffersPage.tsx` — Uses old field names
- **File:** `frontend/rider-web/src/pages/OffersPage.tsx`
- **Line 65:** `offer.discount_value` → should be `offer.value`
- **Line 73:** `offer.end_time` → should be `offer.valid_to`
- **Backend returns:** `{ code, title, description, discount_type, value, max_discount, min_ride_value, valid_from, valid_to, city }`

### 2. driver-app `Incentives.tsx` — Uses old field names
- **File:** `frontend/driver-app/src/screens/Incentives.tsx`
- **Line 48:** `item.bonus_amount` → should be `item.reward_amount`
- **Line 53:** `item.min_distance / item.max_distance` → don't exist, use `item.condition` (JSON)
- **Line 57:** `item.end_time` → should be `item.valid_to`

### 3. driver-app `driverIncentiveService.ts` — Interface mismatches model
- **File:** `frontend/driver-app/src/services/driverIncentiveService.ts`
- **Old fields:** `bonus_amount`, `min_distance`, `max_distance`, `start_time`, `end_time`
- **Correct fields:** `type`, `condition` (JSON), `reward_amount`, `max_per_day`, `valid_from`, `valid_to`
- **Missing:** `type`, `condition`, `reward_amount`, `max_per_day`, `current_progress`

---

## 🟡 MEDIUM — Functional but Wrong Data / Silent Failures

### 4. driver-app `Wallet.tsx` — Calls `/payments/wallet/` without leading `/api/`
- **Line 17:** `api.get("/payments/wallet/")` — uses `/payments/wallet/` with leading slash
- **api.ts baseURL is `http://HOST/api`** → resolves to `http://HOST/payments/wallet/` (missing `/api/`)
- **Fix:** Change to `api.get("payments/wallet/")`
- *(Same issue on Line 49: `api.post("/payments/payout/instant/")`)*

### 5. rider-web `OffersPage.tsx` — Offer type uses old Offer interface
- The service file was fixed (uses `value`, `valid_to`) but the **page component** still reads `offer.discount_value` and `offer.end_time` from the old TypeScript interface.

### 6. driver-app Incentives — No Type/Condition display
- Backend returns `{ type: "STREAK", condition: { rides_required: 5 }, reward_amount: 100 }`
- Frontend shows `Distance: undefined - undefined` because it reads the old `min_distance` / `max_distance` fields.

---

## 🟠 WARNINGS — Missing Features / Incomplete Wiring

### 7. Rider-app has NO payment service file
- The `RideCompletion.tsx` screen calls payment APIs directly via bare `fetch()` or `api.post()`
- There's no `paymentService.ts` — all calls are inline
- **Impact:** Inconsistent, no centralized error handling for payments

### 8. Rider-app has NO ride service file  
- All ride API calls (`request/`, `active/`, `cancel/`, `feedback/`) are done inline in screen files
- No centralized `rideService.ts`
- **Impact:** Code duplication, harder to maintain

### 9. Driver-app has NO ride service file
- Ride accept/reject/complete calls are inline in screen files
- No `rideService.ts`

### 10. Admin dashboard has pages with NO services
- `Drivers.tsx`, `AdminRides.tsx`, `Verification.tsx`, `Payments.tsx`, etc. call `api.get()` directly
- Only `Offers.tsx` and `DriverIncentives.tsx` have dedicated service files
- **Impact:** Code duplication, no type safety

---

## 🔵 NICE TO HAVE — Architecture Improvements

### 11. Rider-web missing several features
- No support ticket creation page (CreateTicketPage.tsx exists but not verified)
- No offer apply integration in BookRide flow

### 12. Driver-app missing features
- No level/score display for drivers (backend has full level system)
- No notification history screen (backend has notification model)
- Driver can't see their own stats/level promotions

### 13. Admin dashboard missing driver level analytics
- Backend has full driver level history (`/drivers/admin/drivers/<id>/level-history/`)
- `Drivers.tsx` fetches it but could display level distribution charts

### 14. No WebSocket reconnection in rider-web
- `rider-web/src/services/socket.ts` connects but no auto-reconnect on failure
- rider-app has offline queue but rider-web doesn't

### 15. Celery Beat schedule not verified
- Tasks exist (`recalculate_all_driver_scores`, `reset_weekly_driver_stats`, `lift_expired_suspensions`, `send_driver_feedback_nudges`)
- Need to verify they're registered in `settings.CELERY_BEAT_SCHEDULE`

---

## ✅ VERIFIED WORKING (No Issues)

| System | Status |
|--------|--------|
| Admin dashboard → Offers CRUD + Analytics | ✅ |
| Admin dashboard → Driver Incentives CRUD + Analytics | ✅ |
| Admin dashboard → Driver list/detail/actions/level | ✅ |
| Admin dashboard → Rides list + resolve | ✅ |
| Admin dashboard → Verification flow | ✅ |
| Admin dashboard → Support tickets | ✅ |
| Admin dashboard → Payments/Payouts/Ledger | ✅ |
| Admin dashboard → Fare Config | ✅ |
| Admin dashboard → Overview/Analytics/Reports | ✅ |
| Admin dashboard → Alerts | ✅ |
| Admin dashboard → Live Map | ✅ |
| Rider-app → Offers list (just fixed) | ✅ |
| Rider-app → Ride flow (search/confirm/track/complete) | ✅ |
| Rider-app → Support tickets | ✅ |
| Rider-web → Ride booking flow | ✅ |
| Rider-web → Ride tracking + SOS | ✅ |
| Rider-web → Payment + Simulate | ✅ |
| Rider-web → Support page | ✅ |
| Driver-app → Ride offer/accept/reject | ✅ |
| Driver-app → Location tracking | ✅ |
| Driver-app → Document upload | ✅ |
| Driver-app → Notifications | ✅ |
| Backend → Complete ride lifecycle | ✅ |
| Backend → Driver level system | ✅ |
| Backend → Abuse detection | ✅ |
| Backend → Progressive suspension | ✅ |
| Backend → Matching with level priority | ✅ |
