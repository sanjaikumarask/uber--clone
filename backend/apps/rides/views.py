# apps/rides/views.py

import logging
from django.shortcuts import get_object_or_404
from django.db import transaction
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

from apps.users.permissions import IsRider, IsDriver
from apps.rides.models import Ride
from apps.rides.services.otp import verify_and_consume_otp
from apps.rides.services.distance import get_planned_route, RoutePlanningError
from apps.rides.services.final_fare import calculate_final_fare
from apps.rides.services.cancellation import cancel_ride
from apps.rides.services.surge_engine import (
    cell_id_from_lat_lng,
    increment_demand,
    decrement_demand,
    increment_supply,
)
from apps.drivers.services.trust import (
    register_completed_ride,
    register_driver_cancellation,
)
from apps.drivers.models import Driver
from apps.rides.kafka import publish_ride_searching_event

logger = logging.getLogger(__name__)


# ============================================================
# CREATE RIDE
# ============================================================
class CreateRideView(APIView):
    permission_classes = [IsAuthenticated, IsRider]

    def post(self, request):
        # 🔒 HARD BLOCK: only ONE active ride per rider
        if Ride.objects.filter(
            rider=request.user,
            status__in=[
                Ride.Status.SEARCHING,
                Ride.Status.ASSIGNED,
                Ride.Status.ARRIVED,
                Ride.Status.ONGOING,
            ],
        ).exists():
            return Response(
                {
                    "error": "Active ride already exists",
                    "code": "ACTIVE_RIDE_EXISTS",
                },
                status=status.HTTP_409_CONFLICT,
            )

        try:
            pickup_lat = float(request.data["pickup_lat"])
            pickup_lng = float(request.data["pickup_lng"])
            drop_lat = float(request.data["drop_lat"])
            drop_lng = float(request.data["drop_lng"])
        except (KeyError, ValueError):
            return Response(
                {"error": "Invalid pickup/drop coordinates"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            route = get_planned_route(
                origin=(pickup_lat, pickup_lng),
                destination=(drop_lat, drop_lng),
            )
        except RoutePlanningError as e:
            logger.exception("Route planning failed")
            return Response(
                {"error": f"Route planning failed: {str(e)}"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        cell_id = cell_id_from_lat_lng(pickup_lat, pickup_lng)

        with transaction.atomic():
            ride = Ride.objects.create(
                rider=request.user,
                pickup_lat=pickup_lat,
                pickup_lng=pickup_lng,
                drop_lat=drop_lat,
                drop_lng=drop_lng,
                status=Ride.Status.SEARCHING,
                planned_route_polyline=route["polyline"],
                planned_distance_km=route["distance_km"],
                planned_duration_min=route["duration_min"],
            )

            increment_demand(cell_id)

            # 🔥 Fire async matching ONLY after commit
            transaction.on_commit(
                lambda r=ride: publish_ride_searching_event(
                    ride=r,
                    driver_ids=[],
                )
            )

        return Response(
            {
                "ride_id": ride.id,
                "status": ride.status,
                "planned_distance_km": ride.planned_distance_km,
                "planned_duration_min": ride.planned_duration_min,
            },
            status=status.HTTP_201_CREATED,
        )


# ============================================================
# VERIFY OTP
# ============================================================
class VerifyOtpView(APIView):
    permission_classes = [IsAuthenticated, IsRider]

    def post(self, request, ride_id):
        ride = get_object_or_404(
            Ride,
            id=ride_id,
            rider=request.user,
            status=Ride.Status.ARRIVED,
        )

        with transaction.atomic():
            verify_and_consume_otp(ride, request.data.get("otp"))
            ride.transition_to(Ride.Status.ONGOING)

        return Response({"status": ride.status})


# ============================================================
# COMPLETE RIDE
# ============================================================
class CompleteRideView(APIView):
    permission_classes = [IsAuthenticated, IsDriver]

    def post(self, request, ride_id):
        with transaction.atomic():
            ride = get_object_or_404(
                Ride.objects.select_for_update(),
                id=ride_id,
                driver__user=request.user,
                status=Ride.Status.ONGOING,
            )

            cell_id = cell_id_from_lat_lng(
                ride.pickup_lat,
                ride.pickup_lng,
            )

            if ride.final_fare is None:
                ride.final_fare = calculate_final_fare(
                    base_fare=ride.base_fare,
                    actual_distance_km=ride.actual_distance_km,
                    surge_cell_id=cell_id,
                )
                ride.save(update_fields=["final_fare"])

            ride.transition_to(Ride.Status.COMPLETED)

            register_completed_ride(ride.driver)

            decrement_demand(cell_id)
            increment_supply(cell_id)

            driver = ride.driver
            driver.status = Driver.Status.ONLINE
            driver.save(update_fields=["status"])

        return Response(
            {
                "status": ride.status,
                "final_fare": str(ride.final_fare),
                "actual_distance_km": round(ride.actual_distance_km, 3),
            }
        )


# ============================================================
# CANCEL RIDE
# ============================================================
class CancelRideView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, ride_id):
        ride = get_object_or_404(Ride, id=ride_id)

        if ride.rider == request.user:
            by = Ride.CancelledBy.RIDER
        elif ride.driver and ride.driver.user == request.user:
            by = Ride.CancelledBy.DRIVER
        else:
            return Response({"error": "Not allowed"}, status=403)

        cell_id = cell_id_from_lat_lng(
            ride.pickup_lat,
            ride.pickup_lng,
        )

        with transaction.atomic():
            cancel_ride(ride=ride, by=by)

            decrement_demand(cell_id)

            if by == Ride.CancelledBy.DRIVER and ride.driver:
                increment_supply(cell_id)
                register_driver_cancellation(ride.driver)

        return Response({"status": ride.status})


class ActiveRideView(APIView):
    permission_classes = [IsAuthenticated, IsRider]

    def get(self, request):
        ride = (
            Ride.objects
            .filter(
                rider=request.user,
                status__in=[
                    Ride.Status.SEARCHING,
                    Ride.Status.ASSIGNED,
                    Ride.Status.ARRIVED,
                    Ride.Status.ONGOING,
                ],
            )
            .order_by("-id")
            .first()
        )

        if not ride:
            return Response(
                {"ride": None},
                status=status.HTTP_200_OK,
            )

        return Response(
            {
                "ride_id": ride.id,
                "status": ride.status,
                "pickup_lat": ride.pickup_lat,
                "pickup_lng": ride.pickup_lng,
                "driver": (
                    {
                        "lat": ride.driver.lat,
                        "lng": ride.driver.lng,
                    }
                    if ride.driver
                    else None
                ),
            },
            status=status.HTTP_200_OK,
        )
