# apps/admin_dashboard/views.py
import logging
from datetime import timedelta

from django.db.models import Avg, Count, Q, Sum
from django.db.models.functions import TruncDate
from django.shortcuts import get_object_or_404
from django.utils.timezone import now
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.drivers.models import Driver
from apps.payments.models import Payment
from apps.rides.fare_models import FareConfig
from apps.rides.models import Ride
from apps.users.permissions import IsAdmin

from .models import SystemLog
from .serializers import (
    AdminDriverSerializer,
    AdminRideSerializer,
    FareConfigSerializer,
    SystemLogSerializer,
)

logger = logging.getLogger(__name__)


# ============================================================
# 1. FARE CONFIG PANEL API
# ============================================================
class AdminFareConfigView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request, pk=None):
        if pk:
            config = get_object_or_404(FareConfig, pk=pk)
            return Response(FareConfigSerializer(config).data)
        configs = FareConfig.objects.all().order_by("vehicle_type")
        serializer = FareConfigSerializer(configs, many=True)
        return Response(serializer.data)

    def patch(self, request, pk):
        config = get_object_or_404(FareConfig, pk=pk)
        serializer = FareConfigSerializer(config, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ============================================================
# 2. LIVE RIDE MONITORING API
# ============================================================
class AdminLiveRidesView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        active_statuses = [
            Ride.Status.SEARCHING,
            Ride.Status.OFFERED,
            Ride.Status.ASSIGNED,
            Ride.Status.ARRIVED,
            Ride.Status.ONGOING,
        ]
        rides = Ride.objects.filter(status__in=active_statuses).select_related(
            "rider", "driver", "driver__user"
        )

        return Response(
            {
                "count": rides.count(),
                "rides": AdminRideSerializer(rides, many=True).data,
            }
        )


# ============================================================
# 3. PAYMENT MONITORING API
# ============================================================
class AdminPaymentStatusView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        today = now().date()
        payments = Payment.objects.filter(created_at__date=today)

        success = payments.filter(status=Payment.Status.CAPTURED).count()
        failed = payments.filter(status=Payment.Status.FAILED).count()
        pending = payments.filter(status=Payment.Status.CREATED).count()

        total_revenue = (
            payments.filter(status=Payment.Status.CAPTURED).aggregate(Sum("amount"))[
                "amount__sum"
            ]
            or 0
        )

        # High failure alert detection
        total = max(success + failed, 1)
        failure_rate = (failed / total) * 100

        alerts = []
        if failure_rate > 15:  # Alert if failure rate > 15%
            alerts.append(
                {
                    "type": "HIGH_FAILURE_RATE",
                    "message": f"Payment failure rate is {failure_rate:.1f}% today.",
                    "level": "CRITICAL",
                }
            )

        # Payment captured but verification missing?
        # (Actually CAPTURED implies verification happened, but we check CREATED for > 30 mins)
        stale_pending = Payment.objects.filter(
            status=Payment.Status.CREATED, created_at__lt=now() - timedelta(minutes=30)
        ).count()

        if stale_pending > 0:
            alerts.append(
                {
                    "type": "STALE_PAYMENTS",
                    "message": f"{stale_pending} payments pending for more than 30 minutes.",
                    "level": "WARNING",
                }
            )

        return Response(
            {
                "summary": {
                    "success": success,
                    "failed": failed,
                    "pending": pending,
                    "total_count": payments.count(),
                    "total_revenue": total_revenue,
                },
                "alerts": alerts,
            }
        )


# ============================================================
# 4. ANALYTICS DASHBOARD API
# ============================================================
class AdminAnalyticsView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):

        # Last 30 days
        start_date = now().date() - timedelta(days=30)

        rides_stats = (
            Ride.objects.filter(created_at__date__gte=start_date)
            .annotate(date=TruncDate("created_at"))
            .values("date")
            .annotate(
                total_count=Count("id"),
                completed_count=Count("id", filter=Q(status=Ride.Status.COMPLETED)),
                cancelled_count=Count("id", filter=Q(status=Ride.Status.CANCELLED)),
                revenue=Sum("final_fare", filter=Q(status=Ride.Status.COMPLETED)),
                avg_distance=Avg(
                    "actual_distance_km", filter=Q(status=Ride.Status.COMPLETED)
                ),
            )
            .order_by("date")
        )

        # Compute lifetime stats
        total_revenue = (
            Ride.objects.filter(status=Ride.Status.COMPLETED).aggregate(
                Sum("final_fare")
            )["final_fare__sum"]
            or 0
        )
        total_completed = Ride.objects.filter(status=Ride.Status.COMPLETED).count()
        total_cancelled = Ride.objects.filter(status=Ride.Status.CANCELLED).count()
        overall_cancellation_rate = (
            total_cancelled / max(total_completed + total_cancelled, 1)
        ) * 100

        return Response(
            {
                "lifetime": {
                    "total_revenue": total_revenue,
                    "total_completed": total_completed,
                    "total_cancelled": total_cancelled,
                    "cancellation_rate": round(overall_cancellation_rate, 2),
                },
                "daily_stats": list(rides_stats),
            }
        )


# ============================================================
# 5. SYSTEM ALERTS PANEL API
# ============================================================
class AdminAlertsView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        alerts = SystemLog.objects.all()[:50]

        # AUTO-GENERATE ALERTS ON THE FLY FOR MONITORING
        stuck_rides = Ride.objects.filter(
            status=Ride.Status.ONGOING, updated_at__lt=now() - timedelta(minutes=45)
        )
        for r in stuck_rides:
            # Check if we already logged this recently
            if not SystemLog.objects.filter(
                type=SystemLog.LogType.RIDE_STUCK, metadata__ride_id=r.id
            ).exists():
                SystemLog.objects.create(
                    type=SystemLog.LogType.RIDE_STUCK,
                    message=f"Ride #{r.id} has been ONGOING for more than 45 mins. Potential driver app kill.",
                    metadata={"ride_id": r.id},
                )

        serializer = SystemLogSerializer(alerts, many=True)
        return Response(serializer.data)


# ============================================================
# 6. DRIVER MANAGEMENT API
# ============================================================
class AdminDriverListView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        # Allow filtering by status
        status_filter = request.query_params.get("status")
        queryset = Driver.objects.all().select_related("user")
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        serializer = AdminDriverSerializer(queryset, many=True)
        return Response(serializer.data)


class AdminDriverActionView(APIView):
    permission_classes = [IsAdmin]

    def post(self, request, driver_id):
        action = request.data.get("action")  # "approve", "reject", "block"
        driver = get_object_or_404(Driver, id=driver_id)

        if action == "approve":
            driver.is_verified = True
            driver.save()
        elif action in {"reject", "block"}:
            driver.is_verified = False
            driver.save()

        return Response({"status": f"Driver {action}ed successfully"})


# ============================================================
# 7. MAP SNAPSHOT (REAL-TIME POLLING FALLBACK)
# ============================================================
class AdminLiveMapSnapshot(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        # Drivers online
        drivers = Driver.objects.exclude(status=Driver.Status.OFFLINE)
        # Active rides
        active_rides = Ride.objects.filter(
            status__in=[Ride.Status.ASSIGNED, Ride.Status.ARRIVED, Ride.Status.ONGOING]
        )

        return Response(
            {
                "drivers": [
                    {
                        "id": d.id,
                        "lat": d.last_lat,
                        "lng": d.last_lng,
                        "status": d.status,
                        "name": d.user.get_full_name(),
                    }
                    for d in drivers
                    if d.last_lat and d.last_lng
                ],
                "rides": [
                    {
                        "id": r.id,
                        "status": r.status,
                        "pickup": [r.pickup_lat, r.pickup_lng],
                        "drop": [r.drop_lat, r.drop_lng],
                        "rider_name": r.rider.get_full_name(),
                        "driver_id": r.driver_id,
                    }
                    for r in active_rides
                ],
            }
        )


# Existing views (refactored or inherited)
class AdminOverviewView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        import time

        from django.core.cache import cache

        from apps.common.adaptive import AdaptiveShedder

        today = now().date()

        # Calculate Real System Health
        start = time.time()
        redis_ok = True
        try:
            cache.set("admin:health:ping", "1", timeout=5)
            redis_latency = f"{int((time.time() - start) * 1000)}ms"
        except Exception:
            redis_ok = False
            redis_latency = "timeout"

        return Response(
            {
                "online_drivers": Driver.objects.filter(
                    status=Driver.Status.ONLINE
                ).count(),
                "busy_drivers": Driver.objects.filter(
                    status=Driver.Status.BUSY
                ).count(),
                "active_rides": Ride.objects.filter(
                    status__in=[
                        Ride.Status.SEARCHING,
                        Ride.Status.OFFERED,
                        Ride.Status.ASSIGNED,
                        Ride.Status.ARRIVED,
                        Ride.Status.ONGOING,
                    ]
                ).count(),
                "completed_today": Ride.objects.filter(
                    status=Ride.Status.COMPLETED, updated_at__date=today
                ).count(),
                "cancelled_today": Ride.objects.filter(
                    status=Ride.Status.CANCELLED, updated_at__date=today
                ).count(),
                "revenue_today": Ride.objects.filter(
                    status=Ride.Status.COMPLETED, updated_at__date=today
                ).aggregate(Sum("final_fare"))["final_fare__sum"]
                or 0,
                # 🔥 Real System Health Object
                "system_health": {
                    "redis": {"ok": redis_ok, "latency": redis_latency},
                    "shedding_factor": round(AdaptiveShedder.get_factor(), 2),
                    "is_operational": AdaptiveShedder.get_factor() < 0.5,
                    "timestamp": now(),
                },
            }
        )


# ============================================================
# 8. SYSTEM LOGS (REDIS STREAM)
# ============================================================
class AdminSystemLogsView(APIView):
    permission_classes = [IsAdmin]
    throttle_classes = []  # 🔥 Disable for log stream

    def get(self, request):
        import json

        import redis
        from django.conf import settings

        try:
            r = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
            # Fetch last 100 log entries
            raw_logs = r.lrange("system:observability:logs", 0, 99)
            from contextlib import suppress
            logs = []
            for raw in raw_logs:
                with suppress(Exception):
                    logs.append(json.loads(raw))
            return Response(logs)
        except Exception as e:
            return Response({"error": str(e)}, status=500)
