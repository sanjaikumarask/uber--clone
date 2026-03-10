# apps/drivers/admin_views.py
"""
Admin Driver Management endpoints.
All endpoints require IsAdmin permission.
"""

import logging

from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.drivers.models import Driver, DriverLevelHistory, DriverStats
from apps.drivers.services.scoring import admin_set_level, recalculate_driver_score
from apps.users.permissions import IsAdmin

logger = logging.getLogger(__name__)


class AdminDriversListView(APIView):
    """
    GET  /api/drivers/admin/drivers/
    Returns all drivers with full metrics. Supports filtering by:
      - status (ONLINE, OFFLINE, BLOCKED, BUSY)
      - level  (NORMAL, ACTIVE, CONSISTENT, PRO)
      - suspended (true | false)
    """

    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        qs = (
            Driver.objects.select_related("user", "stats")
            .all()
            .order_by("-stats__score")
        )

        status = request.query_params.get("status")
        level = request.query_params.get("level")
        suspended = request.query_params.get("suspended")

        if status:
            qs = qs.filter(status=status)
        if level:
            qs = qs.filter(level=level)
        if suspended is not None:
            qs = qs.filter(stats__is_suspended=(suspended.lower() == "true"))

        data = [self._serialize_driver(d) for d in qs]
        return Response(data)

    def _serialize_driver(self, d):
        stats = getattr(d, "stats", None)
        data = {
            "driver_id": d.id,
            "name": d.user.get_full_name() or d.user.username,
            "phone": getattr(d.user, "phone", ""),
            "status": d.status,
            "level": d.level,
            "updated_at": d.updated_at.isoformat(),
        }
        data.update(self._serialize_stats(stats))
        return data

    def _serialize_stats(self, stats):
        return {
            "offered_rides": stats.offered_rides if stats else 0,
            "accepted_rides": stats.accepted_rides if stats else 0,
            "completed_rides": stats.completed_rides if stats else 0,
            "cancelled_rides": stats.cancelled_rides if stats else 0,
            "acceptance_rate": stats.acceptance_rate if stats else 100.0,
            "cancellation_rate": stats.cancellation_rate if stats else 0.0,
            "weekly_rides": stats.weekly_rides if stats else 0,
            "peak_hour_rides": stats.peak_hour_rides if stats else 0,
            "score": stats.score if stats else 0.0,
            "trust_score": stats.trust_score if stats else 100.0,
            "avg_rating": stats.avg_rating if stats else 5.0,
            "fraud_flags": stats.fraud_flags_count if stats else 0,
            "is_suspended": stats.is_suspended if stats else False,
            "suspended_until": (
                stats.suspended_until.isoformat()
                if stats and stats.suspended_until
                else None
            ),
        }


class AdminDriverDetailView(APIView):
    """
    GET /api/drivers/admin/drivers/<id>/
    Full detail for one driver including level history.
    """

    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request, driver_id):
        d = get_object_or_404(
            Driver.objects.select_related("user", "stats"), id=driver_id
        )
        level_history = (
            DriverLevelHistory.objects.filter(driver=d)
            .select_related("changed_by")
            .order_by("-created_at")[:20]
        )

        history_data = [
            {
                "old_level": h.old_level,
                "new_level": h.new_level,
                "changed_by": (
                    h.changed_by.get_full_name() if h.changed_by else "System"
                ),
                "reason": h.reason,
                "timestamp": h.created_at.isoformat(),
            }
            for h in level_history
        ]

        data = self._serialize_driver_detail(d, history_data)
        return Response(data)

    def _serialize_driver_detail(self, d, history_data):
        stats = getattr(d, "stats", None)
        data = {
            "driver_id": d.id,
            "name": d.user.get_full_name() or d.user.username,
            "phone": getattr(d.user, "phone", ""),
            "status": d.status,
            "level": d.level,
            "is_verified": d.is_verified,
            "vehicle_model": d.vehicle_model,
            "vehicle_number": d.vehicle_number,
            "level_history": history_data,
        }
        data.update(AdminDriversListView._serialize_stats(None, stats))
        return data


class AdminDriverActionView(APIView):
    """
    POST /api/drivers/admin/drivers/actions/
    Body: { driver_id, action }
    Actions: suspend | unsuspend | block | unblock | force_offline | recalculate_score
    """

    permission_classes = [IsAuthenticated, IsAdmin]

    def post(self, request):
        driver_id = request.data.get("driver_id")
        action = request.data.get("action")

        VALID_ACTIONS = {
            "suspend",
            "unsuspend",
            "block",
            "unblock",
            "force_offline",
            "recalculate_score",
        }
        if not driver_id or action not in VALID_ACTIONS:
            return Response(
                {"error": f"Invalid params. action must be one of: {VALID_ACTIONS}"},
                status=400,
            )

        driver = get_object_or_404(Driver, id=driver_id)
        stats, _ = DriverStats.objects.get_or_create(driver=driver)

        with transaction.atomic():
            if action == "suspend":
                from datetime import timedelta

                from django.utils import timezone

                stats.is_suspended = True
                stats.suspended_until = timezone.now() + timedelta(hours=24)
                stats.save(
                    update_fields=["is_suspended", "suspended_until", "updated_at"]
                )
                driver.status = Driver.Status.OFFLINE
                driver.save(update_fields=["status", "updated_at"])

            elif action == "unsuspend":
                stats.is_suspended = False
                stats.suspended_until = None
                stats.save(
                    update_fields=["is_suspended", "suspended_until", "updated_at"]
                )
                driver.status = Driver.Status.OFFLINE
                driver.save(update_fields=["status", "updated_at"])

            elif action == "block":
                driver.status = Driver.Status.BLOCKED
                driver.save(update_fields=["status", "updated_at"])

            elif action == "unblock":
                driver.status = Driver.Status.OFFLINE
                stats.is_suspended = False
                stats.save(update_fields=["is_suspended", "updated_at"])
                driver.save(update_fields=["status", "updated_at"])

            elif action == "force_offline":
                driver.status = Driver.Status.OFFLINE
                driver.save(update_fields=["status", "updated_at"])

            elif action == "recalculate_score":
                recalculate_driver_score(driver)

        logger.info(
            f"Admin {request.user.id} performed action '{action}' on driver {driver_id}"
        )
        return Response(
            {
                "success": True,
                "status": driver.status,
                "is_suspended": stats.is_suspended,
            }
        )


class AdminDriverLevelView(APIView):
    """
    POST /api/drivers/admin/drivers/<id>/level/
    Body: { level: "NORMAL" | "ACTIVE" | "CONSISTENT" | "PRO", reason: "..." }
    Manually set a driver's level and log history.
    """

    permission_classes = [IsAuthenticated, IsAdmin]

    def post(self, request, driver_id):
        driver = get_object_or_404(Driver, id=driver_id)
        new_level = request.data.get("level", "").upper()
        reason = request.data.get("reason", "Manual admin update")

        if new_level not in Driver.Level.values:
            return Response(
                {"error": f"Invalid level. Choose from: {Driver.Level.values}"},
                status=400,
            )

        try:
            duration_days = int(request.data.get("duration_days", 7))
            admin_set_level(
                driver,
                new_level,
                admin_user=request.user,
                reason=reason,
                duration_days=duration_days,
            )
        except ValueError as e:
            return Response({"error": str(e)}, status=400)

        return Response(
            {
                "success": True,
                "driver_id": driver.id,
                "new_level": driver.level,
            }
        )


class AdminDriverLevelHistoryView(APIView):
    """
    GET /api/drivers/admin/drivers/<id>/level-history/
    """

    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request, driver_id):
        get_object_or_404(Driver, id=driver_id)
        history = (
            DriverLevelHistory.objects.filter(driver_id=driver_id)
            .select_related("changed_by")
            .order_by("-created_at")[:50]
        )
        data = [
            {
                "old_level": h.old_level,
                "new_level": h.new_level,
                "changed_by": (
                    h.changed_by.get_full_name() if h.changed_by else "System"
                ),
                "reason": h.reason,
                "timestamp": h.created_at.isoformat(),
            }
            for h in history
        ]
        return Response(data)


class AdminDriverRidesHistoryView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request, driver_id):
        from apps.rides.models import Ride
        from apps.rides.serializers import RideDetailSerializer

        rides = (
            Ride.objects.filter(driver_id=driver_id)
            .select_related("rider", "driver__user")
            .order_by("-created_at")[:50]
        )
        serializer = RideDetailSerializer(rides, many=True)
        return Response(serializer.data)


class AdminPendingDocumentsView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        from apps.drivers.models import DriverDocument

        docs = DriverDocument.objects.filter(
            status=DriverDocument.Status.PENDING
        ).select_related("driver", "driver__user")
        data = []
        for doc in docs:
            file_url = doc.file_path
            if doc.image:
                file_url = request.build_absolute_uri(doc.image.url)
            data.append(
                {
                    "id": doc.id,
                    "driver_id": doc.driver.id,
                    "phone": getattr(doc.driver.user, "phone", ""),
                    "type": doc.document_type,
                    "file_path": file_url,
                    "created_at": doc.created_at,
                }
            )
        return Response(data)


class AdminPendingDriversView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        drivers = (
            Driver.objects.filter(is_verified=False)
            .order_by("-created_at")
            .prefetch_related("documents")
            .select_related("user")
        )
        data = []
        for d in drivers:
            docs = d.documents.all()
            if not docs.exists():
                continue
            doc_list = []
            for doc in docs:
                file_url = doc.file_path
                if doc.image:
                    file_url = request.build_absolute_uri(doc.image.url)
                doc_list.append(
                    {
                        "id": doc.id,
                        "type": doc.document_type,
                        "status": doc.status,
                        "file_path": file_url,
                        "rejection_reason": doc.rejection_reason,
                    }
                )
            data.append(
                {
                    "driver_id": d.id,
                    "name": d.user.get_full_name(),
                    "phone": getattr(d.user, "phone", ""),
                    "email": d.user.email,
                    "documents": doc_list,
                    "created_at": d.created_at,
                }
            )
        return Response(data)


class AdminDocumentApprovalView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def post(self, request, doc_id):
        from apps.drivers.models import DriverDocument

        doc = get_object_or_404(DriverDocument, id=doc_id)
        action = request.data.get("action")
        reason = request.data.get("reason", "")

        if action == "approve":
            doc.approve(request.user)
        elif action == "reject":
            if not reason:
                return Response({"error": "Reason required for rejection"}, status=400)
            doc.reject(request.user, reason)
        else:
            return Response({"error": "Invalid action"}, status=400)

        return Response({"success": True, "status": doc.status})
