from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from rest_framework import permissions

from apps.rides.models import Ride

from .models import Payment
from .razorpay_client import razorpay_client
from .views import CreatePaymentOrderView, VerifyPaymentView


class WebCheckoutView(CreatePaymentOrderView):
    """
    Renders the HTML checkout page for Mobile WebViews.
    """

    def get(self, request, ride_id):
        # 1. Reuse logic to create order (but synchronous)
        # We can't use `super().post(request)` directly because it returns DRF Response.
        # We need the context data for the template.

        # NOTE: Using minimal auth for now (Cookie or existing session)
        # Ideally, pass ?token=... for JWT auth manually if WebView doesn't share cookies.
        if not request.user.is_authenticated:
            # Fallback for demo: assume token provided in header or cookie
            # But here we just error or prompt login if not handled
            pass

        # Since we are inheriting, let's just copy payload logic roughly
        # or call a helper. For now duplicating slightly for clarity.

        ride = get_object_or_404(
            Ride,
            id=ride_id,
            rider=request.user,  # Ensure rider matches
        )

        # Just create the order if missing, similar to CreatePaymentOrderView
        # We need to ensure we have a pending Payment record with Order ID

        # ... (logic similar to CreatePaymentOrderView) ...
        # For brevity, let's assume CreatePaymentOrderView logic is extracted or we just do it here.

        if not razorpay_client:
            return HttpResponseRedirect("/payments/error?msg=GatewayConfigMissing")

        # Create/Get Payment
        payment = Payment.objects.filter(
            ride_id=ride.id, status=Payment.Status.CREATED
        ).first()
        if not payment:
            payment = Payment.objects.create(
                user=request.user,
                ride_id=ride.id,
                amount=ride.final_fare,
                status=Payment.Status.CREATED,
            )

        order_id = payment.gateway_order_id
        if not order_id:
            order = razorpay_client.order.create(
                {
                    "amount": int(ride.final_fare * 100),
                    "currency": "INR",
                    "receipt": f"ride_{ride.id}_payment_{payment.id}",
                    "payment_capture": 1,
                }
            )
            payment.gateway_order_id = order["id"]
            payment.save()
            order_id = order["id"]

        context = {
            "key": razorpay_client.auth[0],
            "amount": int(ride.final_fare * 100),
            "currency": "INR",
            "name": "Uber Clone",
            "description": f"Ride #{ride.id}",
            "order_id": order_id,
            "callback_url": "/payments/verify-web/",
            "user": request.user,
            # "csrf_token": ... (handled by Django usually if middleware present)
        }
        return render(request, "payments/checkout.html", context)


class WebVerifyView(VerifyPaymentView):
    """
    Handles form POST from Razorpay Checkout (redirect/callback flow).
    """

    permission_classes = [permissions.AllowAny]  # Callback comes from Browser/Script

    def post(self, request):
        # Extract form data
        data = request.POST
        if not data:
            data = request.data  # In case DRF parser works

        # Verify logic is same as VerifyPaymentView
        # But we need to return HTML success/failure page instead of JSON

        # ... call super().post(request) logic ...
        # But we can't easily reuse super().post because it returns Response objects.

        # Let's extract verification logic to a service if possible, or just duplicate for this fix.
        # ...

        try:
            # Verify
            razorpay_client.utility.verify_payment_signature(
                {
                    "razorpay_order_id": data.get("razorpay_order_id"),
                    "razorpay_payment_id": data.get("razorpay_payment_id"),
                    "razorpay_signature": data.get("razorpay_signature"),
                }
            )

            # Success - Update DB
            # We need to find the payment entry.
            from django.db import transaction

            from apps.payments.services.payout import settle_driver_payout
            from apps.rides.models import Ride

            from .models import LedgerEntry, Payment

            with transaction.atomic():
                payment = Payment.objects.select_for_update().get(
                    gateway_order_id=data.get("razorpay_order_id")
                )
                if payment.status != Payment.Status.CAPTURED:
                    payment.gateway_payment_id = data.get("razorpay_payment_id")
                    payment.gateway_signature = data.get("razorpay_signature")
                    payment.status = Payment.Status.CAPTURED
                    payment.save()

                    # LEDGER & SETTLEMENT logic...
                    LedgerEntry.objects.create(
                        user=payment.user,
                        ride_id=payment.ride_id,
                        amount=payment.amount,
                        entry_type=LedgerEntry.Type.DEBIT,
                        reference=f"payment:{payment.gateway_payment_id}",
                    )
                    ride = Ride.objects.select_for_update().get(id=payment.ride_id)
                    settle_driver_payout(ride=ride, payment=payment)

            return HttpResponseRedirect("/payments/success-page/")  # Or deep link

        except Exception as e:
            return HttpResponseRedirect(f"/payments/error/?msg={e!s}")
