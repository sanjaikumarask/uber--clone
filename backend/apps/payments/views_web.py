import logging

from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from rest_framework import permissions

logger = logging.getLogger(__name__)
from apps.rides.models import Ride

from .models import Payment
from .razorpay_client import razorpay_client
from .views import CreatePaymentOrderView, VerifyPaymentView

from rest_framework_simplejwt.authentication import JWTAuthentication

class QueryParamJWTAuthentication(JWTAuthentication):
    """
    Custom authentication to allow JWT tokens in the query string.
    Needed for Mobile WebViews where headers can't be easily set.
    """
    def authenticate(self, request):
        token = request.query_params.get('token')
        if not token:
            return None # Fallback to other auth methods (like header)
        
        try:
            validated_token = self.get_validated_token(token)
            return self.get_user(validated_token), validated_token
        except Exception:
            return None


class WebCheckoutView(CreatePaymentOrderView):
    """
    Renders the HTML checkout page for Mobile WebViews.
    """

    authentication_classes = [QueryParamJWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, ride_id):
        # 1. Reuse logic to create order (but synchronous)
        # We can't use `super().post(request)` directly because it returns DRF Response.
        # We need the context data for the template.

        if not request.user.is_authenticated:
            return HttpResponseRedirect("/api/payments/error/page/?msg=UnauthorizedAccess")

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
            return HttpResponseRedirect("/api/payments/error/page/?msg=GatewayConfigMissing")

        # 1. Prefer existing payment that already has a Razorpay order
        payment = Payment.objects.filter(
            ride_id=ride.id,
            status=Payment.Status.CREATED,
            gateway_order_id__isnull=False,
        ).first()

        # 2. Fall back to any CREATED payment (no order yet)
        if not payment:
            payment = Payment.objects.filter(
                ride_id=ride.id,
                status=Payment.Status.CREATED,
            ).first()

        # 3. Create payment record if lifecycle didn't make one
        if not payment:
            payment = Payment.objects.create(
                user=request.user,
                ride_id=ride.id,
                amount=ride.final_fare,
                status=Payment.Status.CREATED,
            )

        # 4. Create Razorpay order only if not already created
        try:
            order_id = payment.gateway_order_id
            if not order_id:
                order = razorpay_client.order.create({
                    "amount": int(ride.final_fare * 100),
                    "currency": "INR",
                    "receipt": f"ride_{ride.id}_payment_{payment.id}",
                    "payment_capture": 1,
                })
                payment.gateway_order_id = order["id"]
                payment.save(update_fields=["gateway_order_id"])
                order_id = order["id"]
        except Exception as e:
            logger.error(f"Razorpay Order Creation Failed: {e}")
            return HttpResponseRedirect("/api/payments/error/page/?msg=GatewayError")

        from django.middleware.csrf import get_token
        # Determine if we should force HTTPS for the callback (essential for ngrok/production)
        callback_url = request.build_absolute_uri("/api/payments/verify-web/")
        if not request.is_secure() and not any(h in request.get_host() for h in ["localhost", "127.0.0.1", "10.0.2.2"]):
             callback_url = callback_url.replace("http://", "https://")
        context = {
            "key": razorpay_client.auth[0],
            "amount": int(ride.final_fare * 100),
            "currency": "INR",
            "name": "Tripzo",
            "description": f"Trip #{ride.id}",
            "order_id": order_id,
            "callback_url": callback_url,
            "user": request.user,
            "csrf_token": get_token(request),
        }
        return render(request, "payments/checkout.html", context)


from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

@method_decorator(csrf_exempt, name='dispatch')
class WebVerifyView(VerifyPaymentView):
    """
    Handles form POST from Razorpay Checkout (redirect/callback flow).
    """

    permission_classes = [permissions.AllowAny]

    def post(self, request):
        data = request.POST or request.data
        razorpay_order_id = data.get("razorpay_order_id")
        
        try:
            # 1. Verify payment via Client
            razorpay_client.utility.verify_payment_signature({
                "razorpay_order_id": razorpay_order_id,
                "razorpay_payment_id": data.get("razorpay_payment_id"),
                "razorpay_signature": data.get("razorpay_signature"),
            })

            from django.db import transaction
            from apps.payments.models import Payment, LedgerEntry
            from apps.payments.services.payout import settle_driver_payout
            from apps.rides.models import Ride

            # 2. Process within transaction
            with transaction.atomic():
                payment = Payment.objects.select_for_update().get(gateway_order_id=razorpay_order_id)
                
                # Check status (Webhook might have finished first)
                success_url = request.build_absolute_uri(f"/api/payments/success/page/?ride_id={payment.ride_id}")
                if not request.is_secure() and not any(h in request.get_host() for h in ["localhost", "127.0.0.1", "10.0.2.2"]):
                    success_url = success_url.replace("http://", "https://")

                if payment.status == Payment.Status.CAPTURED:
                    return HttpResponseRedirect(success_url)

                # Update payment
                payment.gateway_payment_id = data.get("razorpay_payment_id")
                payment.gateway_signature = data.get("razorpay_signature")
                payment.status = Payment.Status.CAPTURED
                payment.save()

                # Ledger entry
                LedgerEntry.objects.create(
                    user=payment.user,
                    ride_id=payment.ride_id,
                    amount=payment.amount,
                    entry_type=LedgerEntry.Type.DEBIT,
                    reason=LedgerEntry.Reason.PAYMENT,
                    reference=f"payment:{payment.gateway_payment_id}"
                )

                # Settlement
                ride = Ride.objects.select_for_update().get(id=payment.ride_id)
                try:
                    settle_driver_payout(ride=ride, payment=payment)
                except Exception as e:
                    logger.error(f"WebVerifyView: settlement fail: {e}")

                from apps.notifications.models import Notification
                if ride.driver:
                    transaction.on_commit(
                        lambda: Notification.objects.create(
                            user=ride.driver.user,
                            channel="push",
                            type="RIDE_PAYMENT_RECEIVED",
                            payload={
                                "title": "Payment received",
                                "body": f"Rider paid ₹{payment.amount} for ride #{ride.id}. Earnings credited.",
                                "data": {"ride_id": str(ride.id), "amount": str(payment.amount)},
                            },
                        )
                    )

            return HttpResponseRedirect(success_url)

        except Exception as e:
            logger.error(f"WebVerifyView Error: {e}")
            # Redirect to common failure page or back to summary with error
            error_url = request.build_absolute_uri(f"/api/payments/error/page/?msg={str(e)}")
            if not request.is_secure() and not any(h in request.get_host() for h in ["localhost", "127.0.0.1", "10.0.2.2"]):
                error_url = error_url.replace("http://", "https://")
            return HttpResponseRedirect(error_url)

