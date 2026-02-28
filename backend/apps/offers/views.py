from rest_framework import viewsets, generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from django.db.models import Sum, Count
from django.shortcuts import get_object_or_404
from django.utils import timezone

from .models import Offer, OfferUsage
from .serializers import AdminOfferCreateSerializer, RiderOfferListSerializer
from .selectors import get_active_rider_offers
from .services.offer_engine import OfferEngine
from apps.rides.models import Ride
from apps.users.permissions import IsRider, IsAdmin


class ValidateOfferView(APIView):
    """
    POST /offers/validate/
    Rider can pre-check if an offer code is valid before booking.
    """
    permission_classes = [IsAuthenticated, IsRider]

    def post(self, request):
        code = request.data.get("code")
        ride_value = request.data.get("ride_value", 0)
        city = request.data.get("city")

        if not code:
            return Response({"valid": False, "message": "Offer code is required."}, status=400)

        try:
            offer = OfferEngine.validate_offer(code, request.user, float(ride_value), city)
            discount = OfferEngine.calculate_discount(offer, float(ride_value))
            return Response({
                "valid": True,
                "code": offer.code,
                "title": offer.title,
                "discount": float(discount),
                "discount_type": offer.discount_type,
                "message": f"Discount of ₹{discount:.2f} will be applied!"
            })
        except Exception as e:
            return Response({"valid": False, "message": str(e)}, status=400)


class ApplyOfferView(APIView):
    """
    POST /offers/apply/
    Apply a promo code to an existing ride.
    """
    permission_classes = [IsAuthenticated, IsRider]

    def post(self, request):
        code = request.data.get("code")
        ride_id = request.data.get("ride_id")

        if not code or not ride_id:
            return Response({"success": False, "message": "code and ride_id are required."}, status=400)

        ride = get_object_or_404(Ride, id=ride_id, rider=request.user)

        # Prevent applying to already completed/cancelled rides
        if ride.status in (Ride.Status.COMPLETED, Ride.Status.CANCELLED):
            return Response({"success": False, "message": "Cannot apply offer to a finished ride."}, status=400)

        # Prevent double-applying an offer
        if ride.applied_offer:
            return Response({"success": False, "message": "An offer is already applied to this ride."}, status=400)

        try:
            discount = OfferEngine.apply_offer(ride, code)
            return Response({
                "success": True,
                "discount": float(discount),
                "final_fare_estimate": float(ride.base_fare) - float(discount)
            })
        except Exception as e:
            return Response({"success": False, "message": str(e)}, status=400)


class AdminOfferViewSet(viewsets.ModelViewSet):
    """
    Admin full CRUD on Offers.
    GET/POST  /offers/admin/
    GET/PUT/PATCH/DELETE /offers/admin/<id>/
    """
    queryset = Offer.objects.all().order_by("-created_at")
    serializer_class = AdminOfferCreateSerializer
    permission_classes = [IsAdmin]

    @action(detail=True, methods=["post"])
    def deactivate(self, request, pk=None):
        offer = self.get_object()
        offer.is_active = False
        offer.save(update_fields=["is_active"])
        return Response({"status": "deactivated"})

    @action(detail=True, methods=["post"])
    def activate(self, request, pk=None):
        offer = self.get_object()
        offer.is_active = True
        offer.save(update_fields=["is_active"])
        return Response({"status": "activated"})


class RiderOfferListView(generics.ListAPIView):
    """
    GET /offers/active/?city=Chennai
    Returns active, unexpired offers valid for the given city.
    """
    serializer_class = RiderOfferListSerializer
    permission_classes = [IsAuthenticated, IsRider]

    def get_queryset(self):
        city = self.request.query_params.get("city")
        return get_active_rider_offers(city=city)


class OfferAnalyticsView(APIView):
    """
    GET /offers/admin/analytics/
    Admin monitoring: total discounts given, per-offer breakdown, daily trend.
    """
    permission_classes = [IsAdmin]

    def get(self, request):
        total_discounts = (
            OfferUsage.objects.aggregate(total=Sum("discount_applied"))["total"] or 0
        )

        per_offer = (
            OfferUsage.objects.values("offer__id", "offer__code", "offer__title")
            .annotate(
                usage_count=Count("id"),
                total_discount=Sum("discount_applied"),
            )
            .order_by("-usage_count")
        )

        # Daily discount trend last 7 days
        from django.db.models.functions import TruncDate
        daily = (
            OfferUsage.objects.filter(
                created_at__date__gte=(timezone.now().date() - timezone.timedelta(days=7))
            )
            .annotate(date=TruncDate("created_at"))
            .values("date")
            .annotate(total=Sum("discount_applied"), count=Count("id"))
            .order_by("date")
        )

        return Response({
            "total_discounts_given": float(total_discounts),
            "per_offer_breakdown": list(per_offer),
            "daily_last_7_days": list(daily),
        })
