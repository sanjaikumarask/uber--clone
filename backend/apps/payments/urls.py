from django.urls import path

from .views import CreatePaymentOrderView, VerifyPaymentView, SimulatedPaymentView
from .views_refund import RefundPaymentView
from .views_wallet import WalletBalanceView
from .views_payout import DriverPayoutRequestView
from .views_web import WebCheckoutView, WebVerifyView
from .webhooks import razorpay_webhook, payout_webhook

app_name = "payments"

urlpatterns = [
    path("create/<int:ride_id>/", CreatePaymentOrderView.as_view()),
    path("verify/", VerifyPaymentView.as_view()),
    path("simulate/<int:ride_id>/", SimulatedPaymentView.as_view()),
    path("refund/<int:payment_id>/", RefundPaymentView.as_view()),

    # Web Checkout (for Mobile WebViews)
    path("checkout/<int:ride_id>/", WebCheckoutView.as_view()),
    path("verify-web/", WebVerifyView.as_view()),

    # Webhooks
    path("webhook/razorpay/", razorpay_webhook),
    path("webhook/payout/", payout_webhook),

    # Wallet
    path("wallet/", WalletBalanceView.as_view()),

    # Driver
    path("payout/", DriverPayoutRequestView.as_view()),
    path("payout/instant/", DriverPayoutRequestView.as_view()),
]
