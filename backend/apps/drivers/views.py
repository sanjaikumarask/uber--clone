# apps/drivers/views.py

from datetime import timedelta
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.core.exceptions import ValidationError

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from apps.users.permissions import IsDriver
from apps.drivers.models import Driver
from apps.rides.models import Ride
from apps.rides.services.otp import (
    generate_and_attach_otp,
    verify_and_consume_otp,
)


# =====================================================
# DRIVER PROFILE
# =====================================================

class DriverProfileView(APIView):
    permission_classes = [IsDriver]

    def get(self, request):
        driver = request.user.driver
        return Response({
            "id": driver.id,
            "status": driver.status,
        })


# =====================================================
# GO ONLINE
# =====================================================

class GoOnlineView(APIView):
    permission_classes = [IsDriver]

    def post(self, request):
        driver = request.user.driver
        driver.status = Driver.Status.ONLINE
        driver.save(update_fields=["status"])
        return Response({"status": driver.status})


# =====================================================
# GO OFFLINE
# =====================================================

class GoOfflineView(APIView):
    permission_classes = [IsDriver]

    def post(self, request):
        driver = request.user.driver

        if Ride.objects.filter(
            driver=driver,
            status__in=[
                Ride.Status.ASSIGNED,
                Ride.Status.ARRIVED,
                Ride.Status.ONGOING,
            ],
        ).exists():
            return Response(
                {"error": "Cannot go offline during active ride"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        driver.status = Driver.Status.OFFLINE
        driver.save(update_fields=["status"])
        return Response({"status": driver.status})


# =====================================================
# UPDATE LOCATION
# =====================================================

class UpdateLocationView(APIView):
    permission_classes = [IsDriver]

    def post(self, request):
        driver = request.user.driver

        try:
            driver.last_lat = float(request.data["lat"])
            driver.last_lng = float(request.data["lng"])
        except (KeyError, ValueError):
            return Response(
                {"error": "lat and lng required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        driver.save(update_fields=["last_lat", "last_lng"])
        return Response({"ok": True})


# =====================================================
# ACCEPT RIDE
# =====================================================

class AcceptRideView(APIView):
    permission_classes = [IsDriver]

    @transaction.atomic
    def post(self, request, ride_id):
        driver = request.user.driver

        if driver.status != Driver.Status.ONLINE:
            return Response(
                {"error": "Driver must be ONLINE"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        ride = (
            Ride.objects
            .select_for_update()
            .filter(
                id=ride_id,
                status=Ride.Status.SEARCHING,
                driver__isnull=True,
            )
            .first()
        )

        if not ride:
            return Response(
                {"error": "Ride not available"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        ride.driver = driver
        ride.transition_to(Ride.Status.ASSIGNED)

        driver.status = Driver.Status.BUSY
        driver.save(update_fields=["status"])

        return Response({"status": ride.status})


# =====================================================
# REJECT RIDE  ✅ REQUIRED BY URLS
# =====================================================

class RejectRideView(APIView):
    permission_classes = [IsDriver]

    def post(self, request, ride_id):
        return Response({"status": "rejected"})


# =====================================================
# DRIVER ARRIVED → GENERATE OTP
# =====================================================

class DriverArrivedView(APIView):
    permission_classes = [IsDriver]

    @transaction.atomic
    def post(self, request, ride_id):
        ride = get_object_or_404(
            Ride.objects.select_for_update(),
            id=ride_id,
            driver=request.user.driver,
            status=Ride.Status.ASSIGNED,
        )

        ride.transition_to(Ride.Status.ARRIVED)
        ride.arrived_at = timezone.now()
        generate_and_attach_otp(ride)

        ride.save(update_fields=[
            "status",
            "arrived_at",
            "otp_code",
            "otp_expires_at",
        ])

        return Response({"status": ride.status})


# =====================================================
# START RIDE WITH OTP  ✅ REQUIRED BY URLS
# =====================================================
class StartRideWithOTPView(APIView):
    permission_classes = [IsDriver]

    @transaction.atomic
    def post(self, request, ride_id):
        ride = get_object_or_404(
            Ride.objects.select_for_update(),
            id=ride_id,
            driver=request.user.driver,
            status=Ride.Status.ARRIVED,
        )

        if not ride.otp_verified_at:
            return Response(
                {"error": "OTP not verified by rider"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        ride.transition_to(Ride.Status.ONGOING)
        return Response({"status": ride.status})


# =====================================================
# NO SHOW
# =====================================================

class MarkNoShowView(APIView):
    permission_classes = [IsDriver]

    @transaction.atomic
    def post(self, request, ride_id):
        ride = get_object_or_404(
            Ride.objects.select_for_update(),
            id=ride_id,
            driver=request.user.driver,
            status=Ride.Status.ARRIVED,
        )

        if timezone.now() < ride.arrived_at + timedelta(minutes=5):
            return Response(
                {"error": "Wait time not completed"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        ride.transition_to(Ride.Status.NO_SHOW)

        driver = request.user.driver
        driver.status = Driver.Status.ONLINE
        driver.save(update_fields=["status"])

        return Response({"status": ride.status})
