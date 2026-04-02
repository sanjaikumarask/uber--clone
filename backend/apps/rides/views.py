import logging
from decimal import Decimal

from django.db import models, transaction
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.backpressure import endpoint_cooldown
from apps.common.idempotency import idempotent_request
from apps.drivers.models import Driver, DriverStats
from apps.rides.models import Ride
from apps.rides.serializers import RideDetailSerializer
from apps.rides.services.cancellation import cancel_ride
from apps.rides.services.distance import get_planned_route
from apps.rides.services.fare import estimate_fare
from apps.rides.services.matching import find_driver_and_offer_ride
from apps.rides.services.otp import verify_and_consume_otp
from apps.rides.services.surge_engine import cell_id_from_lat_lng, increment_demand
from apps.users.permissions import IsDriver, IsRider

logger = logging.getLogger(__name__)


class EstimateFareView(APIView):
    """
    Rider-facing view to get price & route preview before booking.
    """

    permission_classes = [IsAuthenticated, IsRider]

    def post(self, request):
        logger.info(f"EstimateFareView received: {request.data}")

        required_keys = ["pickup_lat", "pickup_lng", "drop_lat", "drop_lng"]
        missing_keys = [key for key in required_keys if key not in request.data]

        if missing_keys:
            return Response(
                {"error": f"Missing required fields: {', '.join(missing_keys)}"},
                status=400,
            )

        try:
            pickup_lat = float(request.data["pickup_lat"])
            pickup_lng = float(request.data["pickup_lng"])
            drop_lat = float(request.data["drop_lat"])
            drop_lng = float(request.data["drop_lng"])

            # 1. Get distance/duration ONCE
            from apps.rides.services.distance import get_distance_and_duration
            try:
                dist_km, dur_min = get_distance_and_duration((pickup_lat, pickup_lng), (drop_lat, drop_lng))
            except:
                dist_km, dur_min = 5.0, 15.0

            # 2. Estimate for ALL active configs
            from apps.rides.fare_models import FareConfig
            all_configs = FareConfig.objects.filter(is_active=True)
            
            prices_map = {}
            for config in all_configs:
                data = estimate_fare(
                    (pickup_lat, pickup_lng), (drop_lat, drop_lng),
                    vehicle_type=config.type,
                    distance_km=dist_km,
                    duration_min=dur_min
                )
                prices_map[config.type] = float(data["estimated_fare"])

            # Use 'go' or first available as the primary one for polyline/discount preview
            primary_fare = prices_map.get("go", list(prices_map.values())[0] if prices_map else 0)
            
            route = get_planned_route((pickup_lat, pickup_lng), (drop_lat, drop_lng))

            # --- Support Promo Code ---
            promo_code = request.data.get("promo_code")
            discount = 0
            if promo_code:
                from apps.offers.services.offer_engine import OfferEngine
                try:
                    offer = OfferEngine.validate_offer(promo_code, request.user, float(primary_fare), "Chennai")
                    discount = OfferEngine.calculate_discount(offer, float(primary_fare))
                except:
                    pass

            return Response(
                {
                    "estimated_fare": float(primary_fare),
                    "discount_applied": float(discount),
                    "final_estimate": float(primary_fare) - float(discount),
                    "prices": prices_map, # New map for UI
                    "distance_km": float(dist_km),
                    "duration_min": float(dur_min),
                    "surge_multiplier": float(estimate_fare((pickup_lat, pickup_lng), (drop_lat, drop_lng), distance_km=dist_km, duration_min=dur_min)["surge_multiplier"]),
                    "polyline": route["polyline"],
                }
            )
        except Exception as e:
            logger.error(f"Fare estimation failed: {e}")
            return Response({"error": f"Failed to estimate fare: {e!s}"}, status=400)


class CreateRideView(APIView):
    permission_classes = [IsAuthenticated, IsRider]

    @idempotent_request(ttl=300)
    def post(self, request):
        if not self._check_rate_limit(request.user.id):
            return Response({"error": "Too many ride requests. Please wait."}, status=429)

        active_ride = self._get_active_ride(request.user)
        if active_ride:
            return Response({"error": "Active ride exists", "ride_id": active_ride.id}, status=409)

        try:
            coords = self._extract_coords(request.data)
            if "error" in coords:
                return Response({"error": coords["error"]}, status=400)

            if not self._validate_coords(coords):
                return Response({"error": "Coordinates out of bounds"}, status=400)

            vehicle_type = request.data.get("vehicle_type", "go")
            fare_data = estimate_fare(
                (coords["pickup_lat"], coords["pickup_lng"]),
                (coords["drop_lat"], coords["drop_lng"]),
                vehicle_type,
            )
            route = get_planned_route(
                (coords["pickup_lat"], coords["pickup_lng"]),
                (coords["drop_lat"], coords["drop_lng"]),
            )
        except (KeyError, ValueError, TypeError) as e:
            logger.error(f"Ride creation input validation failed: {str(e)} | Data: {request.data}")
            return Response({"error": f"Invalid coordinates or missing fields: {e!s}"}, status=400)
        except Exception as e:
            logger.error(f"Unexpected error during ride prep: {str(e)} | Type: {type(e)}")
            return Response({"error": f"Failed to prepare ride request: {str(e)}"}, status=500)

        try:
            with transaction.atomic():
                ride = self._create_ride_object(request, coords, vehicle_type, fare_data, route)
                self._apply_promo(ride, request.data.get("promo_code"))
                increment_demand(cell_id_from_lat_lng(coords["pickup_lat"], coords["pickup_lng"]))
                self._broadcast_ride_created(ride)
                transaction.on_commit(lambda: find_driver_and_offer_ride(ride.id))

            serializer = RideDetailSerializer(ride)
            return Response(serializer.data, status=201)
        except Exception as e:
            logger.error(f"Ride creation database error: {e}")
            return Response({"error": "Database error during ride creation"}, status=500)

    def _check_rate_limit(self, user_id):
        if not endpoint_cooldown(user_id, "create_ride", max_calls=3, window=60):
            logger.warning(f"[AbuseDiscovery] User {user_id} hit create_ride limit")
            return False
        return True

    def _get_active_ride(self, user):
        return Ride.objects.filter(
            rider=user,
            status__in=[
                Ride.Status.SEARCHING,
                Ride.Status.OFFERED,
                Ride.Status.ASSIGNED,
                Ride.Status.ARRIVED,
                Ride.Status.ONGOING,
            ],
        ).first()

    def _extract_coords(self, data):
        pickup_lat = data.get("pickup_lat") or data.get("pickupLat")
        pickup_lng = data.get("pickup_lng") or data.get("pickupLng")
        drop_lat = data.get("drop_lat") or data.get("dropLat")
        drop_lng = data.get("drop_lng") or data.get("dropLng")

        if any(v is None for v in [pickup_lat, pickup_lng, drop_lat, drop_lng]):
            missing = [k for k, v in {"pickup_lat": pickup_lat, "pickup_lng": pickup_lng, "drop_lat": drop_lat, "drop_lng": drop_lng}.items() if v is None]
            return {"error": f"Missing required coordinates: {', '.join(missing)}"}

        return {
            "pickup_lat": float(pickup_lat),
            "pickup_lng": float(pickup_lng),
            "drop_lat": float(drop_lat),
            "drop_lng": float(drop_lng),
        }

    def _validate_coords(self, coords):
        return (-90 <= coords["pickup_lat"] <= 90 and
                -180 <= coords["pickup_lng"] <= 180 and
                -90 <= coords["drop_lat"] <= 90 and
                -180 <= coords["drop_lng"] <= 180)

    def _create_ride_object(self, request, coords, vehicle_type, fare_data, route):
        return Ride.objects.create(
            rider=request.user,
            pickup_lat=coords["pickup_lat"],
            pickup_lng=coords["pickup_lng"],
            pickup_address=request.data.get("pickup_address", "Pickup Point"),
            drop_lat=coords["drop_lat"],
            drop_lng=coords["drop_lng"],
            drop_address=request.data.get("drop_address", "Destination"),
            status=Ride.Status.SEARCHING,
            vehicle_type=vehicle_type,
            planned_route_polyline=route["polyline"],
            planned_distance_km=fare_data["distance_km"],
            planned_duration_min=fare_data["duration_min"],
            base_fare=fare_data["estimated_fare"],
            city=request.data.get("city", "Chennai"),
        )

    def _apply_promo(self, ride, promo_code):
        if promo_code:
            from apps.offers.services.offer_engine import OfferEngine
            try:
                OfferEngine.apply_offer(ride, promo_code)
            except Exception as e:
                logger.warning(f"Failed to apply promo {promo_code} to ride {ride.id}: {e}")

    def _broadcast_ride_created(self, ride):
        from asgiref.sync import async_to_sync
        from channels.layers import get_channel_layer
        layer = get_channel_layer()
        data = {
            "ride_id": ride.id,
            "status": "SEARCHING",
            "rider_id": ride.rider_id,
            "rider_name": ride.rider.get_full_name() or ride.rider.username,
            "vehicle_type": ride.vehicle_type,
            "pickup": {"lat": float(ride.pickup_lat), "lng": float(ride.pickup_lng)},
            "drop": {"lat": float(ride.drop_lat), "lng": float(ride.drop_lng)},
        }
        transaction.on_commit(lambda: async_to_sync(layer.group_send)(
            "admin_live_map", {"type": "admin_generic_event", "event": "RIDE_CREATED", "data": data}
        ))


# --- Simulation / Testing View (BYPASS DRIVER APP) ---
class SimulateActionView(APIView):
    """
    Bypass driver app for testing END-TO-END flow from the rider app.
    Supports actions: ACCEPT, ARRIVE, START, COMPLETE
    """
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, ride_id):
        from django.core.exceptions import ValidationError as DjangoValidationError

        action = request.data.get("action")
        ride = get_object_or_404(Ride, id=ride_id)

        # Basic security: only YOUR ride (unless admin)
        if ride.rider != request.user and not request.user.is_staff:
             return Response({"error": "Unauthorized"}, status=403)

        from apps.rides.services.lifecycle import update_ride_status
        from apps.drivers.models import Driver
        
        if action == "ACCEPT":
             # Idempotent: already assigned, return success immediately
             if ride.status == Ride.Status.ASSIGNED:
                 return Response({"status": ride.status, "message": "Already accepted"})

             # Use the Bot Driver 70
             try:
                 driver = Driver.objects.get(id=70)
                 # Auto-unblock for simulation
                 if driver.status == Driver.Status.BLOCKED:
                     driver.status = Driver.Status.ONLINE
                     driver.save(update_fields=["status"])
                     from apps.drivers.models import DriverStats
                     stats, _ = DriverStats.objects.get_or_create(driver=driver.user)
                     stats.is_suspended = False
                     stats.suspended_until = None
                     stats.save(update_fields=["is_suspended", "suspended_until"])
             except Driver.DoesNotExist:
                 # Fallback to first available driver if 70 is missing
                 driver = Driver.objects.first()
                 if not driver:
                     return Response({"error": "No drivers available in DB"}, status=400)
             
             ride.driver = driver
             ride.save(update_fields=["driver"])

             # Reset surge for simulation rides to avoid inflated test fares
             try:
                 from apps.rides.fare_models import FareConfig
                 from decimal import Decimal
                 config = FareConfig.objects.filter(
                     vehicle_type=ride.vehicle_type, is_active=True
                 ).first()
                 if config and config.surge_multiplier > Decimal("1.5"):
                     config.surge_multiplier = Decimal("1.0")
                     config.save(update_fields=["surge_multiplier"])
             except Exception:
                 pass

             # Transition status safely (broadcasts to WS)
             try:
                 update_ride_status(ride, Ride.Status.ASSIGNED)
             except (DjangoValidationError, Exception) as e:
                 logger.warning(f"SimulateAction ACCEPT failed for ride {ride_id}: {e}")
                 return Response({"error": str(e)}, status=400)

             return Response({"status": ride.status, "message": f"Driver {driver.user.first_name} Accepted!"})

        elif action == "ARRIVE":
             if ride.status == Ride.Status.ARRIVED:
                 return Response({"status": ride.status})
             try:
                 update_ride_status(ride, Ride.Status.ARRIVED)
             except (DjangoValidationError, Exception) as e:
                 logger.warning(f"SimulateAction ARRIVE failed for ride {ride_id}: {e}")
                 return Response({"error": str(e)}, status=400)
             return Response({"status": ride.status})

        elif action == "START":
             if ride.status == Ride.Status.ONGOING:
                 return Response({"status": ride.status})
             try:
                 if ride.driver and ride.driver.id == 70:
                     ride.start_lat, ride.start_lng = ride.pickup_lat, ride.pickup_lng
                     ride.save(update_fields=["start_lat", "start_lng"])
                 update_ride_status(ride, Ride.Status.ONGOING)
             except (DjangoValidationError, Exception) as e:
                 logger.warning(f"SimulateAction START failed for ride {ride_id}: {e}")
                 return Response({"error": str(e)}, status=400)
             return Response({"status": ride.status})

        elif action == "COMPLETE":
             if ride.status == Ride.Status.COMPLETED:
                 return Response({"status": "COMPLETED"})
             
             if ride.driver and ride.driver.id == 70:
                 if not ride.start_lat:
                     ride.start_lat, ride.start_lng = ride.pickup_lat, ride.pickup_lng
                 ride.save(update_fields=["start_lat", "start_lng"])
                 
                 # Clear any accumulated surge in Redis before calculating final fare
                 try:
                     import redis
                     from django.conf import settings
                     r = redis.Redis.from_url(settings.REDIS_URL)
                     keys = r.keys('geo:*:surge') + r.keys('demand:*') + r.keys('surge:*')
                     if keys:
                         r.delete(*keys)
                 except Exception:
                     pass

             # Force calculation call to populate final_fare
             try:
                 from apps.rides.services.complete_ride import complete_ride
                 complete_ride(ride_id=ride.id)
             except Exception as e:
                 logger.warning(f"SimulateAction COMPLETE failed for ride {ride_id}: {e}")
                 return Response({"error": str(e)}, status=400)
             return Response({"status": "COMPLETED"})

        return Response({"error": "Invalid action"}, status=400)


# --- Ride Lifecycle Actions (Idempotent) ---
class AcceptRideView(APIView):
    permission_classes = [IsAuthenticated, IsDriver]

    @idempotent_request(ttl=300)
    def post(self, request, ride_id):
        # ── BACKPRESSURE: API Throttling ──
        if not endpoint_cooldown(
            request.user.id, "accept_ride", max_calls=10, window=30
        ):
            return Response(
                {"error": "Too many attempts. Please slow down."}, status=429
            )
        logger.info(
            f"AcceptRideView: user={request.user.id} attempting to accept ride_id={ride_id}"
        )

        # DEBUG: Check ride state before selecting for update
        ride_exists = Ride.objects.filter(id=ride_id).first()
        if not ride_exists:
            logger.error(f"AcceptRideView: Ride {ride_id} does not exist.")
        else:
            logger.info(
                f"AcceptRideView: Ride {ride_id} current status={ride_exists.status}, driver_id={ride_exists.driver_id}"
            )

        with transaction.atomic():
            # Use filter().first() instead of get_object_or_404 to provide better error messages
            ride = (
                Ride.objects.select_for_update()
                .filter(
                    id=ride_id, driver__user=request.user, status=Ride.Status.OFFERED
                )
                .first()
            )

            if not ride:
                # If we are here, it means the query above failed.
                # Let's find out why.
                actual_ride = Ride.objects.filter(id=ride_id).first()
                if not actual_ride:
                    return Response({"error": "Ride not found"}, status=404)

                error_msg = f"Cannot accept ride {ride_id}. "
                if actual_ride.status != Ride.Status.OFFERED:
                    error_msg += f"Status is {actual_ride.status} (expected OFFERED)."
                if not actual_ride.driver or actual_ride.driver.user != request.user:
                    error_msg += (
                        f"Ride is NOT assigned to you (User {request.user.id})."
                    )

                logger.warning(f"AcceptRideView: {error_msg}")
                return Response({"error": error_msg}, status=400)

            # Ensure driver is BUSY
            driver = ride.driver
            driver.status = Driver.Status.BUSY
            driver.save(update_fields=["status"])

            from apps.rides.services.lifecycle import update_ride_status

            update_ride_status(ride, Ride.Status.ASSIGNED)

            # Track accepted ride for metrics
            from apps.drivers.services.metrics import update_driver_metrics

            update_driver_metrics(driver, "ACCEPTED")

        logger.info(
            f"AcceptRideView: Ride {ride.id} successfully ACCEPTED by Driver {driver.id}"
        )
        return Response({"status": ride.status})


# ... (RejectRideView is the same) ...
class RejectRideView(APIView):
    permission_classes = [IsAuthenticated, IsDriver]

    @idempotent_request(ttl=300)
    def post(self, request, ride_id):
        logger.info(
            f"RejectRideView: user={request.user.id} rejecting ride_id={ride_id}"
        )

        with transaction.atomic():
            ride = (
                Ride.objects.select_for_update()
                .filter(
                    id=ride_id, driver__user=request.user, status=Ride.Status.OFFERED
                )
                .first()
            )

            if not ride:
                logger.warning(
                    f"RejectRideView: Ride {ride_id} not eligible for rejection by User {request.user.id}"
                )
                return Response(
                    {"error": "Ride not eligible for rejection"}, status=400
                )

            driver = ride.driver
            from apps.drivers.services.metrics import update_driver_metrics

            update_driver_metrics(driver, "REJECTED")

            ride.driver = None
            ride.status = Ride.Status.SEARCHING
            rj = ride.rejected_driver_ids or []
            if driver.id not in rj:
                rj.append(driver.id)
            ride.rejected_driver_ids = rj
            ride.save(
                update_fields=["driver", "status", "rejected_driver_ids", "updated_at"]
            )

            transaction.on_commit(lambda: find_driver_and_offer_ride(ride.id))

        logger.info(f"RejectRideView: Driver {driver.id} rejected ride {ride.id}")
        return Response({"status": "REJECTED"})


# ============================================================
# DRIVER ARRIVED (Moved from Driver App)
# ============================================================
from apps.rides.services.lifecycle import update_ride_status


class DriverArrivedView(APIView):
    permission_classes = [IsAuthenticated, IsDriver]

    def post(self, request, ride_id):
        with transaction.atomic():
            ride = get_object_or_404(
                Ride.objects.select_for_update(),
                id=ride_id,
                driver__user=request.user,
                status=Ride.Status.ASSIGNED,
            )
            update_ride_status(ride, Ride.Status.ARRIVED)
        return Response({"status": ride.status})


# ============================================================
# START RIDE — Verify OTP + Lock start_time, start_lat, start_lng
# POST /rides/{id}/start/
# Called by: DRIVER
# ============================================================
class VerifyOtpView(APIView):
    permission_classes = [IsAuthenticated, IsDriver]

    @idempotent_request(ttl=300)
    def post(self, request, ride_id):
        # ── BACKPRESSURE: API Throttling ──
        if not endpoint_cooldown(
            request.user.id, "verify_otp", max_calls=15, window=60
        ):
            return Response(
                {"error": "Too many OTP attempts. Please wait."}, status=429
            )
        otp = request.data.get("otp")
        driver_lat = request.data.get("lat")
        driver_lng = request.data.get("lng")

        if not otp:
            return Response(
                {"error": "OTP is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        with transaction.atomic():
            ride = get_object_or_404(
                Ride.objects.select_for_update(),
                id=ride_id,
                driver__user=request.user,
            )

            # ── Guard 1: Already started (idempotent) ──
            if ride.status == Ride.Status.ONGOING:
                return Response(
                    {"status": "already_started", "start_time": ride.start_time},
                    status=status.HTTP_200_OK,
                )

            # ── Guard 2: Only allowed from ARRIVED ──
            if ride.status != Ride.Status.ARRIVED:
                return Response(
                    {
                        "error": f"Cannot start ride from status '{ride.status}'. Driver must arrive first."
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # ── OTP BRUTE FORCE PROTECTION ──
            from apps.drivers.redis import redis_client

            otp_attempt_key = f"otp_attempts:{ride.id}"
            attempts = int(redis_client.get(otp_attempt_key) or 0)

            if attempts >= 5:
                # Flag as potential fraud and block further attempts
                ride.is_fraud_flagged = True
                ride.save(update_fields=["is_fraud_flagged"])
                logger.warning(
                    f"OTP Brute Force detected for Ride {ride.id} by User {request.user.id}"
                )
                return Response(
                    {
                        "error": "Too many failed OTP attempts. This ride is flagged for security review. Please contact support."
                    },
                    status=status.HTTP_429_TOO_MANY_REQUESTS,
                )

            # ── OTP Verification ──
            try:
                verify_and_consume_otp(ride, otp)  # Raises ValidationError if wrong
            except Exception as e:
                # Increment attempts on failure
                redis_client.incr(otp_attempt_key)
                redis_client.expire(otp_attempt_key, 600)  # 10 minute lockout window
                raise e

            # ── Lock start_lat / start_lng if provided ──
            if driver_lat and driver_lng:
                try:
                    ride.start_lat = float(driver_lat)
                    ride.start_lng = float(driver_lng)
                    ride.save(update_fields=["start_lat", "start_lng"])
                except (TypeError, ValueError):
                    pass  # GPS optional, don't block start

            # ── Transition ARRIVED → ONGOING (locks start_time inside lifecycle) ──
            update_ride_status(ride, Ride.Status.ONGOING)

        logger.info(
            f"StartRide: Ride {ride.id} started by Driver {ride.driver.id}. "
            f"start_time={ride.start_time}, gps=({ride.start_lat},{ride.start_lng})"
        )
        return Response(
            {
                "status": ride.status,
                "start_time": ride.start_time,
                "start_lat": ride.start_lat,
                "start_lng": ride.start_lng,
            }
        )


# ============================================================
# COMPLETE RIDE
# POST /rides/{id}/complete/
# Called by: DRIVER
# ============================================================
class CompleteRideView(APIView):
    permission_classes = [IsAuthenticated, IsDriver]

    @idempotent_request(ttl=300)
    def post(self, request, ride_id):
        # ── BACKPRESSURE: API Throttling ──
        if not endpoint_cooldown(
            request.user.id, "complete_ride", max_calls=10, window=60
        ):
            return Response(
                {"error": "Too many complete requests. Please wait."}, status=429
            )

        # ── Complete Ride (fare calculation + status + broadcasts) ──
        # This is done OUTSIDE the above lock to let complete_ride() get its own lock
        try:
            from apps.rides.services.complete_ride import complete_ride

            ride = complete_ride(ride_id)
        except Exception as e:
            logger.error(f"CompleteRide: Failed for ride {ride_id}: {e}", exc_info=True)
            return Response(
                {"error": "Failed to complete the ride. Please try again."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        logger.info(
            f"CompleteRide: Ride {ride.id} completed. "
            f"end_time={ride.end_time}, final_fare=₹{ride.final_fare}"
        )
        return Response(
            {
                "status": ride.status,
                "end_time": ride.end_time,
                "start_time": ride.start_time,
                "final_fare": str(ride.final_fare),
                "actual_distance_km": round(ride.actual_distance_km, 2),
            }
        )


class MarkNoShowView(APIView):
    permission_classes = [IsAuthenticated, IsDriver]

    def post(self, request, ride_id):
        with transaction.atomic():
            ride = get_object_or_404(
                Ride.objects.select_for_update(),
                id=ride_id,
                driver__user=request.user,
                status=Ride.Status.ARRIVED,
            )

            # Simple check (uncomment for production)
            # if timezone.now() < ride.arrived_at + timedelta(minutes=5):
            #     return Response({"error": "Wait time not completed"}, status=400)

            ride.transition_to(Ride.Status.NO_SHOW)
            driver = ride.driver
            driver.status = Driver.Status.ONLINE
            driver.save(update_fields=["status"])

        return Response({"status": ride.status})


# ... (CompleteRideView, CancelRideView, UpdateDestinationView, ActiveRideView remain the same) ...


class CancelRideView(APIView):
    permission_classes = [IsAuthenticated]

    @idempotent_request(ttl=300)
    def post(self, request, ride_id):
        # ── BACKPRESSURE: API Throttling ──
        if not endpoint_cooldown(
            request.user.id, "cancel_ride", max_calls=10, window=60
        ):
            return Response(
                {"error": "Too many cancel requests. Please wait."}, status=429
            )

        with transaction.atomic():
            # 🔒 Lock the ride row to avoid race conditions with start_ride/complete_ride
            ride = get_object_or_404(Ride.objects.select_for_update(), id=ride_id)

            # Already cancelled? (Idempotent success)
            if ride.status == Ride.Status.CANCELLED:
                return Response({"status": "CANCELLED"})

            # BUG FIX: Allow admin/staff to cancel rides
            if request.user.is_staff or request.user.is_superuser:
                cancel_ride(ride=ride, by=Ride.CancelledBy.ADMIN)
            elif ride.rider == request.user:
                cancel_ride(ride=ride, by=Ride.CancelledBy.RIDER)
            elif ride.driver and ride.driver.user == request.user:
                cancel_ride(ride=ride, by=Ride.CancelledBy.DRIVER)
            else:
                return Response({"error": "No permission"}, status=403)

        return Response({"status": "CANCELLED"})


class UpdateDestinationView(APIView):
    permission_classes = [IsAuthenticated, IsRider]

    def post(self, request, ride_id):
        try:
            ride = get_object_or_404(Ride, id=ride_id, rider=request.user)

            if ride.status != Ride.Status.ONGOING:
                return Response(
                    {"error": f"Ride {ride_id} is not ONGOING. Cannot update destination."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            drop_lat = request.data.get("drop_lat") or request.data.get("dropLat")
            drop_lng = request.data.get("drop_lng") or request.data.get("dropLng")

            if not drop_lat or not drop_lng:
                return Response(
                    {"error": "drop_lat and drop_lng are required"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            with transaction.atomic():
                ride.drop_lat = float(drop_lat)
                ride.drop_lng = float(drop_lng)
                # In a real app, we'd recalculate fare and route here
                ride.save(update_fields=["drop_lat", "drop_lng", "updated_at"])

            logger.info(f"Ride {ride.id} destination updated to ({drop_lat}, {drop_lng})")
            return Response({"status": "UPDATED", "drop_lat": ride.drop_lat, "drop_lng": ride.drop_lng})
        except Exception as e:
            logger.error(f"Failed to update destination for ride {ride_id}: {e}")
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ActiveRideView(APIView):
    permission_classes = [IsAuthenticated, IsRider]

    def get(self, request):
        ride = Ride.objects.filter(
            rider=request.user,
            status__in=[
                Ride.Status.SEARCHING,
                Ride.Status.OFFERED,
                Ride.Status.ASSIGNED,
                Ride.Status.ARRIVED,
                Ride.Status.ONGOING,
            ],
        ).first()

        if not ride:
            return Response({"id": None})

        serializer = RideDetailSerializer(ride)
        return Response(serializer.data)


class RideDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, ride_id):
        ride = get_object_or_404(Ride, id=ride_id)

        # BUG FIX: Allow admin/staff to view ride details
        if not (request.user.is_staff or request.user.is_superuser):
            if ride.rider != request.user and (
                not ride.driver or ride.driver.user != request.user
            ):
                return Response({"error": "Forbidden"}, status=403)

        serializer = RideDetailSerializer(ride)
        return Response(serializer.data)


class RideHistoryView(APIView):
    """Get ride history for the authenticated user (Rider or Driver)"""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        rides = (
            Ride.objects.filter(
                models.Q(rider=user) | models.Q(driver__user=user),
                status__in=[Ride.Status.COMPLETED, Ride.Status.CANCELLED],
            )
            .select_related("driver", "rider", "driver__user")
            .order_by("-created_at")[:50]
        )

        serializer = RideDetailSerializer(rides, many=True)
        return Response(serializer.data)


class SubmitFeedbackView(APIView):
    """
    Riders can rate Drivers, and Drivers can rate Riders.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, ride_id):
        ride = get_object_or_404(Ride, id=ride_id, status=Ride.Status.COMPLETED)
        user = request.user

        rating = request.data.get("rating")
        comment = request.data.get("comment", "")

        if not rating or not (1 <= int(rating) <= 5):
            return Response({"error": "Rating must be between 1 and 5"}, status=400)

        from apps.rides.models import RideFeedback
        from apps.users.models import RiderStats

        with transaction.atomic():
            if user.role == "rider":
                resp = self._handle_rider_feedback(ride, user, rating, comment)
                if resp: return resp
            elif user.role == "driver":
                resp = self._handle_driver_feedback(ride, user, rating, comment)
                if resp: return resp
            else:
                return Response({"error": "Invalid role for feedback"}, status=400)

        return Response({"success": True})

    def _handle_rider_feedback(self, ride, user, rating, comment):
        from apps.rides.models import RideFeedback
        if ride.rider != user and not user.is_admin:
            return Response({"error": "Unauthorized"}, status=403)

        if RideFeedback.objects.filter(ride=ride, giver_role=RideFeedback.GiverRole.RIDER).exists():
            return Response({"error": "Feedback already submitted"}, status=400)

        RideFeedback.objects.create(
            ride=ride, rider=ride.rider, driver=ride.driver,
            giver_role=RideFeedback.GiverRole.RIDER, rating=int(rating), comment=comment,
        )
        stats, _ = DriverStats.objects.get_or_create(driver=ride.driver.user)
        stats.update_rating(int(rating))
        return None

    def _handle_driver_feedback(self, ride, user, rating, comment):
        from apps.rides.models import RideFeedback
        from apps.users.models import RiderStats
        if (not ride.driver or ride.driver.user != user) and not user.is_admin:
            return Response({"error": "Unauthorized"}, status=403)

        if RideFeedback.objects.filter(ride=ride, giver_role=RideFeedback.GiverRole.DRIVER).exists():
            return Response({"error": "Feedback already submitted"}, status=400)

        RideFeedback.objects.create(
            ride=ride, rider=ride.rider, driver=ride.driver,
            giver_role=RideFeedback.GiverRole.DRIVER, rating=int(rating), comment=comment,
        )
        stats, _ = RiderStats.objects.get_or_create(user=ride.rider)
        stats.update_rating(int(rating))
        return None


class NearbyDriversView(APIView):
    """
    Rider-facing view to see available drivers within a radius (e.g. 5km).
    Used to show car icons on the map before booking.
    Now allows public access to improve initial app experience.
    """

    permission_classes = [AllowAny]

    def post(self, request):
        try:
            data = request.data
            lat = float(data.get("lat"))
            lng = float(data.get("lng"))
            radius_km = float(data.get("radius_km", 5))
            limit = int(data.get("limit", 10))
        except (KeyError, ValueError, TypeError):
            return Response({"error": "Valid 'lat' and 'lng' are required"}, status=400)

        from apps.drivers.services.geo import get_nearby_driver_ids

        driver_ids = get_nearby_driver_ids(
            lat=lat, lng=lng, radius_km=radius_km, limit=limit
        )

        # Fetch basic info for these drivers
        drivers = []
        db_drivers = Driver.objects.filter(
            id__in=driver_ids, status=Driver.Status.ONLINE
        ).select_related("user")

        for d in db_drivers:
            drivers.append(
                {
                    "id": d.id,
                    "lat": d.last_lat,
                    "lng": d.last_lng,
                    "vehicle_type": "go",  # default
                    "name": d.user.get_full_name() or d.user.username,
                }
            )

        # DEBUG: Return total count for troubleshooting
        total_online = Driver.objects.filter(status=Driver.Status.ONLINE).count()

        return Response(
            {
                "drivers": drivers,
                "all_online_count": total_online,
                "nearby_ids": driver_ids,
            }
        )


# ============================================================
# FARE CONFIG READ API
# GET /rides/fare-config/              → all vehicle configs
# GET /rides/fare-config/?type=go      → single vehicle config
# ============================================================
class FareConfigView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from apps.rides.fare_models import FareConfig

        vehicle_type = request.query_params.get("type")

        if vehicle_type:
            config = FareConfig.get_for(vehicle_type)
            return Response(_serialize_config(config))

        # Return all vehicle configs
        configs = FareConfig.objects.filter(is_active=True).order_by("vehicle_type")
        if not configs.exists():
            # Seed defaults on first call
            _seed_default_fare_configs()
            configs = FareConfig.objects.filter(is_active=True).order_by("vehicle_type")

        return Response([_serialize_config(c) for c in configs])


def _serialize_config(c) -> dict:
    return {
        "vehicle_type": c.vehicle_type,
        "name": c.get_vehicle_type_display(),
        "base_fare": str(c.base_fare),
        "base_distance_km": str(c.base_distance_km),
        "per_km_rate": str(c.per_km_rate),
        "waiting_free_minutes": c.waiting_free_minutes,
        "waiting_per_minute": str(c.waiting_per_minute),
        "surge_multiplier": str(c.surge_multiplier),
        "minimum_fare": str(c.minimum_fare),
        "platform_commission_pct": str(c.platform_commission_pct),
    }


def _seed_default_fare_configs():
    """Creates default FareConfig rows for all vehicle types if none exist."""
    from decimal import Decimal

    from apps.rides.fare_models import FareConfig

    defaults = [
        {
            "vehicle_type": "moto",
            "base_fare": "45.00",
            "per_km_rate": "12.00",
            "minimum_fare": "45.00",
        },
        {
            "vehicle_type": "auto",
            "base_fare": "50.00",
            "per_km_rate": "15.00",
            "minimum_fare": "50.00",
        },
        {
            "vehicle_type": "go",
            "base_fare": "59.00",
            "per_km_rate": "18.00",
            "minimum_fare": "60.00",
        },
        {
            "vehicle_type": "xl",
            "base_fare": "80.00",
            "per_km_rate": "24.00",
            "minimum_fare": "80.00",
        },
    ]
    for d in defaults:
        FareConfig.objects.get_or_create(
            vehicle_type=d["vehicle_type"],
            defaults={k: Decimal(v) for k, v in d.items() if k != "vehicle_type"},
        )


# ============================================================
# RIDE FARE BREAKDOWN
# GET /rides/{id}/fare-breakdown/
# Used by: Rider App → Trip Summary Screen
# ============================================================
class RideFareBreakdownView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, ride_id):
        ride = get_object_or_404(Ride, id=ride_id)

        # Only the rider or driver of this ride can view the breakdown
        is_rider = ride.rider == request.user
        is_driver = ride.driver and ride.driver.user == request.user
        is_admin = request.user.is_staff or request.user.is_superuser

        if not (is_rider or is_driver or is_admin):
            return Response({"error": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)

        if ride.status != Ride.Status.COMPLETED:
            return Response(
                {"error": "Fare breakdown is only available for completed rides."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from apps.rides.services.final_fare import get_fare_breakdown

        breakdown = get_fare_breakdown(ride)

        return Response(breakdown)


# ============================================================
# TIP SYSTEM
# POST /rides/{id}/tip/
# Called by: RIDER after payment is complete
# ============================================================
class TipView(APIView):
    """
    Rider adds a tip after completing payment.
    Rules:
      - Ride must be COMPLETED
      - Tip must be > ₹0
      - Tip is stored separately from final_fare
      - 100% of tip credited to driver earnings
      - Idempotent: calling twice replaces (does NOT stack) the tip
    """

    permission_classes = [IsAuthenticated, IsRider]

    def post(self, request, ride_id):
        # ── Parse tip amount ──────────────────────────────────────────
        try:
            tip_amount = Decimal(str(request.data.get("tip_amount", 0)))
        except Exception:
            return Response(
                {"error": "Invalid tip_amount. Must be a positive number."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from decimal import Decimal as D

        MIN_TIP = D("1.00")
        MAX_TIP = D("1000.00")

        if tip_amount < MIN_TIP:
            return Response(
                {"error": f"Tip must be at least ₹{MIN_TIP}."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if tip_amount > MAX_TIP:
            return Response(
                {"error": f"Tip cannot exceed ₹{MAX_TIP}."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            ride = get_object_or_404(
                Ride.objects.select_for_update(of=("self",)).select_related(
                    "driver", "rider"
                ),
                id=ride_id,
            )

            # ── Guard: Only the rider of this ride ────────────────────
            if ride.rider != request.user:
                return Response(
                    {"error": "Only the rider of this trip can add a tip."}, status=403
                )

            # ── Guard: Only on COMPLETED rides ────────────────────────
            if ride.status != Ride.Status.COMPLETED:
                return Response(
                    {"error": "Tips can only be added to completed rides."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # ── Guard: Must have a driver ─────────────────────────────
            if not ride.driver:
                return Response(
                    {"error": "No driver assigned to this ride."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # ── Guard: Payment must be captured ───────────────────────
            from apps.payments.models import Payment

            payment = Payment.objects.filter(
                ride_id=ride.id, status=Payment.Status.CAPTURED
            ).first()
            if not payment:
                return Response(
                    {"error": "Please complete payment before adding a tip."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # ── Idempotent: adjust delta if tip already existed ───────
            previous_tip = ride.tip_amount or Decimal("0.00")
            tip_delta = tip_amount - previous_tip  # Can be 0 or positive

            # Update tip on ride
            ride.tip_amount = tip_amount
            ride.save(update_fields=["tip_amount"])

            # ── Credit tip to driver earnings ─────────────────────────
            if tip_delta > 0:
                from apps.payments.models import DriverEarnings, LedgerEntry

                # Update or create driver earnings record
                earning = getattr(ride, "earning", None)
                if earning:
                    earning.amount += tip_delta
                    earning.net_earning += tip_delta
                    earning.save(update_fields=["amount", "net_earning"])
                else:
                    DriverEarnings.objects.create(
                        driver=ride.driver,
                        ride=ride,
                        amount=tip_delta,
                        commission=Decimal("0.00"),
                        net_earning=tip_delta,
                    )

                # Immutable ledger entry
                LedgerEntry.objects.create(
                    user=ride.driver.user,
                    ride_id=ride.id,
                    payment=payment,
                    amount=tip_delta,
                    entry_type=LedgerEntry.Type.CREDIT,
                    reason=LedgerEntry.Reason.DRIVER_EARNING,
                    reference=f"tip:{ride.id}:{request.user.id}",
                )

                # Notify driver of tip
                from apps.notifications.models import Notification

                transaction.on_commit(
                    lambda: Notification.objects.create(
                        user=ride.driver.user,
                        channel="push",
                        type="TIP_RECEIVED",
                        payload={
                            "title": "You received a tip! 🎉",
                            "body": f"Your rider tipped you ₹{tip_amount} for ride #{ride.id}.",
                            "data": {"ride_id": str(ride.id), "tip": str(tip_amount)},
                        },
                    )
                )

        logger.info(
            f"TipView: Ride {ride.id} — rider {request.user.id} added tip ₹{tip_amount}"
        )
        return Response(
            {
                "status": "tip_recorded",
                "ride_id": ride.id,
                "tip_amount": str(tip_amount),
                "total_with_tip": str(
                    (ride.final_fare + tip_amount).quantize(Decimal("0.01"))
                ),
            }
        )
