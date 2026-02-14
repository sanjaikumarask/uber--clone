from django.urls import path

from .views import CreatePaymentOrderView, VerifyPaymentView
from .views_refund import RefundPaymentView
from .views_wallet import WalletBalanceView
from .views_payout import DriverPayoutRequestView
from .webhooks import razorpay_webhook, payout_webhook
from .admin_views import (
    AdminPaymentsView,
    AdminApprovePayoutView,
    AdminRejectPayoutView,
    AdminLedgerCheckView,
)

app_name = "payments"

urlpatterns = [
    path("create/<int:ride_id>/", CreatePaymentOrderView.as_view()),
    path("verify/", VerifyPaymentView.as_view()),
    path("refund/<int:payment_id>/", RefundPaymentView.as_view()),

    # Webhooks
    path("webhook/razorpay/", razorpay_webhook, name="razorpay-webhook"),
    path("webhook/payout/", payout_webhook, name="payout-webhook"),

    # Wallet
    path("wallet/", WalletBalanceView.as_view()),

    # Admin
    path("admin/payments/", AdminPaymentsView.as_view()),
    path("admin/ledger/check/", AdminLedgerCheckView.as_view()),
    path("admin/payout/approve/<int:payout_id>/", AdminApprovePayoutView.as_view()),
    path("admin/payout/reject/<int:payout_id>/", AdminRejectPayoutView.as_view()),

    # Driver
    path("payout/", DriverPayoutRequestView.as_view()),
]
