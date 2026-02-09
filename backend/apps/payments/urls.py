from django.urls import path
from .views import CreatePaymentOrderView, VerifyPaymentView
from .views_refund import RefundPaymentView
from .webhooks import razorpay_webhook
from .views_wallet import WalletBalanceView

urlpatterns = [
    path("create/<int:ride_id>/", CreatePaymentOrderView.as_view()),
    path("verify/", VerifyPaymentView.as_view()),
    path("refund/<int:payment_id>/", RefundPaymentView.as_view()),
    path("webhook/razorpay/", razorpay_webhook),
    path("wallet/", WalletBalanceView.as_view()),
]
