from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    AdminLoginView,
    DriverLoginView,
    MeView,
    RegisterView,
    RegisterRequestView,
    RiderLoginView,
    UpdatePushTokenView,
    ForgotPasswordView,
    ResetPasswordView,
    VerifyOTPView,
    SocialAuthView,
    DeleteAccountView,
    SavedAddressListView,
    SavedAddressDetailView,
    StaticContentView,
    facebook_proxy,
    google_proxy,
    WalletView,
    ReferralView,
    RiderRideHistoryView,
    CreateComplaintView,
    ChangePasswordView,
)




urlpatterns = [
    path("register/", RegisterView.as_view()),
    path("register/request/", RegisterRequestView.as_view()),
    path("login/", RiderLoginView.as_view()),  # rider
    path("driver-login/", DriverLoginView.as_view()),  # driver
    path("admin-login/", AdminLoginView.as_view()),  # admin
    path("token/refresh/", TokenRefreshView.as_view()),  # 🔥 NEW: JWT Token refresh
    path("me/", MeView.as_view()),
    path("push-token/update/", UpdatePushTokenView.as_view()),
    # 🆕 PASS_RESET FLOW:
    path("forgot-password/", ForgotPasswordView.as_view()),
    path("verify-otp/", VerifyOTPView.as_view()),
    path("reset-password/", ResetPasswordView.as_view()),
    path("delete-account/", DeleteAccountView.as_view()),
    # 🆕 Social Auth
    path("social-auth/", SocialAuthView.as_view()),
    # 🆕 Saved Addresses
    path("addresses/", SavedAddressListView.as_view()),
    path("addresses/<int:pk>/", SavedAddressDetailView.as_view()),
    # 🆕 Static Content (About Us, etc)
    path("content/<slug:key>/", StaticContentView.as_view()),
    # 🛡️ Auth Proxies for Social Logins
    path("google-proxy/", google_proxy, name="google-proxy"),
    path("facebook-proxy/", facebook_proxy, name="facebook-proxy"),
    # 🆕 APP FEATURES HUB:
    path("wallet/", WalletView.as_view()),
    path("referral/", ReferralView.as_view()),
    path("history/", RiderRideHistoryView.as_view()),
    path("complaint/", CreateComplaintView.as_view()),
    path("change-password/", ChangePasswordView.as_view()),
]


