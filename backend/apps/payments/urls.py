from django.urls import path

from .views import CreatePaymentOrderView, VerifyPaymentView, SimulatedPaymentView
from .views_refund import RefundPaymentView
from .views_wallet import WalletBalanceView
from .views_payout import DriverPayoutRequestView
from .views_web import WebCheckoutView, WebVerifyView
from .webhooks import razorpay_webhook, payout_webhook

app_name = "payments"

urlpatterns = [
    path("create/<int:ride_id>/", CreatePaymentOrderView.as_view(), name="create-order"),
    path("verify/", VerifyPaymentView.as_view(), name="verify-payment"),
    path("simulate/<int:ride_id>/", SimulatedPaymentView.as_view(), name="simulate-payment"),
    path("refund/<int:payment_id>/", RefundPaymentView.as_view(), name="refund-payment"),

    # Web Checkout (for Mobile WebViews)
    path("checkout/<int:ride_id>/", WebCheckoutView.as_view(), name="web-checkout"),
    path("verify-web/", WebVerifyView.as_view(), name="web-verify"),

    # Webhooks
    path("webhook/razorpay/", razorpay_webhook, name="razorpay-webhook"),
    path("webhook/payout/", payout_webhook, name="payout-webhook"),

    # Wallet
    path("wallet/", WalletBalanceView.as_view(), name="wallet-balance"),

    # Driver
    path("payout/", DriverPayoutRequestView.as_view(), name="payout-request"),
    path("payout/instant/", DriverPayoutRequestView.as_view(), name="payout-instant"),
]
