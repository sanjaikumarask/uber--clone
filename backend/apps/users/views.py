import sys
import random
import requests
from django.shortcuts import redirect
from rest_framework import permissions, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Q
from rest_framework_simplejwt.tokens import RefreshToken
from django.core.cache import cache
from django.views.decorators.csrf import csrf_exempt

from .serializers import (
    AdminLoginSerializer,
    DriverLoginSerializer,
    RegisterSerializer,
    RiderLoginSerializer,
    UserSerializer,
    SavedAddressSerializer,
    StaticContentSerializer,
)


def jwt_tokens(user):
    refresh = RefreshToken.for_user(user)
    return {
        "refresh": str(refresh),
        "access": str(refresh.access_token),
    }


class RegisterRequestView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)
        phone = request.data.get("phone")
        email = request.data.get("email")
        otp = str(random.randint(100000, 999999))
        identifier = email or phone
        cache.set(f"otp_signup_{identifier}", otp, timeout=600)
        if email:
            from django.core.mail import send_mail
            from django.conf import settings
            try:
                send_mail(
                    subject="Your Tripzo Verification Code",
                    message=f"Your verification code is: {otp}",
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[email],
                    fail_silently=False,
                )
            except Exception as e:
                sys.stderr.write(f"\n[EMAIL_ERROR] Failed to send: {str(e)}\n")
        sys.stderr.write(f"\n[SIGNUP_OTP] OTP for {identifier}: {otp}\n")
        return Response({"status": "OTP sent", "phone": phone, "email": email})

class RegisterView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        otp = request.data.get("otp")
        email = request.data.get("email")
        if not all([otp, email]):
             return Response({"error": "OTP and Email are required"}, status=400)
        cached_otp = cache.get(f"otp_signup_{email}")
        if not cached_otp or str(cached_otp) != str(otp):
             return Response({"error": "Invalid or expired OTP"}, status=400)
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        cache.delete(f"otp_signup_{email}")
        if user.email:
            from django.db import transaction
            from apps.notifications.models import Notification
            transaction.on_commit(
                lambda: Notification.objects.create(
                    user=user,
                    channel="email",
                    type="WELCOME_EMAIL",
                    payload={
                        "subject": "Welcome to Uber Clone!",
                        "body": "Hi, thanks for joining us!",
                    },
                )
            )
        data = jwt_tokens(user)
        data["user"] = UserSerializer(user).data
        return Response(data, status=201)

class RiderLoginView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    def post(self, request):
        serializer = RiderLoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)
        user = serializer.validated_data["user"]
        data = jwt_tokens(user)
        data["user"] = UserSerializer(user).data
        return Response(data)

class DriverLoginView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    def post(self, request):
        serializer = DriverLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        data = jwt_tokens(user)
        data["user"] = UserSerializer(user).data
        return Response(data)

class AdminLoginView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    def post(self, request):
        serializer = AdminLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        data = jwt_tokens(user)
        data["user"] = UserSerializer(user).data
        return Response(data)

class MeView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        user_data = UserSerializer(request.user).data
        return Response(user_data)
    def patch(self, request):
        serializer = UserSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

class UpdatePushTokenView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        token = request.data.get("token")
        if not token:
            return Response({"error": "Token is required"}, status=400)
        request.user.expo_push_token = token
        request.user.save(update_fields=["expo_push_token"])
        return Response({"status": "Token updated"})

class ForgotPasswordView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    def post(self, request):
        value = request.data.get("phone")
        if not value:
            return Response({"error": "Identifier is required"}, status=400)
        from .models import User
        user = User.objects.filter(Q(phone=value) | Q(email=value)).first()
        if not user:
            return Response({"status": "OTP sent if account exists"})
        otp = str(random.randint(100000, 999999))
        cache.set(f"otp_reset_{user.phone}", otp, timeout=600)
        sys.stderr.write(f"\n[PASS_RESET] OTP: {otp}\n")
        return Response({"status": "User found", "phone": user.phone})

class ResetPasswordView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    def post(self, request):
        phone = request.data.get("phone")
        otp = request.data.get("otp")
        new_password = request.data.get("password")
        if not all([phone, otp, new_password]):
            return Response({"error": "All fields are required"}, status=400)
        cached_otp = cache.get(f"otp_reset_{phone}")
        if not cached_otp or str(cached_otp) != str(otp):
             return Response({"error": "Invalid or expired OTP"}, status=400)
        from .models import User
        user = User.objects.filter(Q(phone=phone) | Q(email=phone)).first()
        if not user:
            return Response({"error": "User not found"}, status=404)
        user.set_password(new_password)
        user.save()
        return Response({"status": "Password reset successful"})

class VerifyOTPView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        phone = request.data.get("phone")
        otp = request.data.get("otp")
        cached_otp = cache.get(f"otp_reset_{phone}")
        if not cached_otp or str(cached_otp) != str(otp):
             return Response({"error": "Invalid or expired OTP"}, status=400)
        return Response({"status": "OTP verified"})

class SocialAuthView(APIView):
    """
    🛠️ OPTIMIZED Social Auth: 
    Supports Google ID-Token detection & Backend Cache for double-hits.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        provider = request.data.get("provider")
        token = request.data.get("token")
        
        if not provider or not token:
            return Response({"error": "Provider and Token are required"}, status=400)

        # 🛡️ FIX 3: Backend Cache Handshake (Prevents Double External Calls)
        cache_key = f"oauth_{provider}_{token[-20:]}"
        cached_result = cache.get(cache_key)
        if cached_result:
            sys.stderr.write(f"[OAUTH_DEBUG] 🚩 CACHE HIT: Returning login for {provider}\n")
            sys.stderr.flush()
            return Response(cached_result)

        uid = None
        email = None
        name = "Social User"
        
        try:
            if provider == "google":
                # 🛡️ FIX 2: Check if token is JWT (id_token) or Opaque (access_token)
                is_id_token = token.startswith('eyJ')
                
                if is_id_token:
                    # Direct Google ID-Token Endpoint
                    sys.stderr.write(f"[OAUTH_DEBUG] Routing to ID-Token verify.\n")
                    resp = requests.get(f"https://oauth2.googleapis.com/tokeninfo?id_token={token}", timeout=10)
                else:
                    # Google Access-Token Endpoint
                    sys.stderr.write(f"[OAUTH_DEBUG] Routing to Access-Token verify.\n")
                    resp = requests.get(f"https://www.googleapis.com/oauth2/v1/userinfo?access_token={token}", timeout=10)
                
                if resp.status_code != 200:
                     sys.stderr.write(f"[OAUTH_ERROR] Google API reject: {resp.text}\n")
                     return Response({"error": "Invalid Google token"}, status=401)
                
                data = resp.json()
                uid = data.get("sub") or data.get("id")
                email = data.get("email")
                name = data.get("name", name)
                
            elif provider == "facebook":
                # Check for FB token prefix as instructed
                is_fb_token = token.startswith('EAA')
                if not is_fb_token:
                    sys.stderr.write(f"[OAUTH_WARNING] Facebook token does not start with EAA prefix.\n")

                sys.stderr.write(f"[OAUTH_DEBUG] Verifying Facebook Graph Token...\n")
                resp = requests.get(f"https://graph.facebook.com/me?fields=id,name,email&access_token={token}", timeout=10)
                
                if resp.status_code != 200:
                     sys.stderr.write(f"[OAUTH_ERROR] Facebook API reject: {resp.text}\n")
                     return Response({"error": "Invalid Facebook token"}, status=401)
                
                data = resp.json()
                uid = data.get("id")
                email = data.get("email")
                name = data.get("name", name)

            if not uid:
                 return Response({"error": "Identity extraction failed"}, status=400)

        except Exception as e:
            sys.stderr.write(f"[OAUTH_ERROR] Social Provider Unavailable: {str(e)}\n")
            return Response({"error": "Provider verification failed"}, status=503)

        # Unified Link Account Logic
        from .models import SocialAccount, User
        import random
        
        social_acc = SocialAccount.objects.filter(provider=provider, uid=uid).first()
        if social_acc:
            user = social_acc.user
        else:
            user = User.objects.filter(email=email).first() if email else None
            if not user:
                username = f"{provider}_{random.randint(10000,99999)}"
                user = User.objects.create(username=username, email=email, first_name=name, role=User.ROLE_RIDER)
                user.set_unusable_password()
                user.provider = provider
                user.save()
            SocialAccount.objects.get_or_create(user=user, provider=provider, uid=uid)

        from rest_framework_simplejwt.tokens import RefreshToken
        refresh = RefreshToken.for_user(user)
        result = {
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': {
                'id': user.id, 'email': user.email, 'first_name': user.first_name, 'role': user.role
            }
        }
        
        # 🛡️ Cache hit result for 60s
        cache.set(cache_key, result, timeout=60)
        return Response(result)

class DeleteAccountView(APIView):
    permission_classes = [IsAuthenticated]
    def delete(self, request):
        user = request.user
        user.is_active = False
        user.save()
        return Response({"status": "Account deactivated successfully"})

class SavedAddressListView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        from .models import SavedAddress
        addresses = SavedAddress.objects.filter(user=request.user)
        serializer = SavedAddressSerializer(addresses, many=True)
        return Response(serializer.data)
    def post(self, request):
        serializer = SavedAddressSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(user=request.user)
        return Response(serializer.data, status=201)

class SavedAddressDetailView(APIView):
    permission_classes = [IsAuthenticated]
    def get_object(self, pk, user):
        from .models import SavedAddress
        try:
            return SavedAddress.objects.get(pk=pk, user=user)
        except SavedAddress.DoesNotExist:
            return None
    def put(self, request, pk):
        address = self.get_object(pk, request.user)
        if not address: return Response({"error": "Address not found"}, status=404)
        serializer = SavedAddressSerializer(address, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
    def delete(self, request, pk):
        address = self.get_object(pk, request.user)
        if not address: return Response({"error": "Address not found"}, status=404)
        address.delete()
        return Response(status=204)

class StaticContentView(APIView):
    permission_classes = [AllowAny]
    def get(self, request, key):
        from .models import StaticContent
        content = StaticContent.objects.filter(key=key).first()
        if not content: return Response({"error": "Content not found"}, status=404)
        serializer = StaticContentSerializer(content)
        return Response(serializer.data)

def _get_proxy_html(provider, request):
    from django.http import HttpResponse
    return HttpResponse(f"""
        <html>
        <body style="background:#f7f9fc; display:flex; flex-direction:column; justify-content:center; align-items:center; height:100vh; font-family:sans-serif;">
            <div style="padding:40px; background:white; border-radius:20px; box-shadow:0 10px 25px rgba(0,0,0,0.05); text-align:center;">
                <div style="border:4px solid rgba(0,0,0,0.1); width:40px; height:40px; border-radius:50%; border-left-color:#E53935; animation:spin 1s linear infinite; margin:0 auto 20px;"></div>
                <h2 style="margin:0 0 10px; color:#333;">Finalizing {provider.capitalize()}...</h2>
                <p style="color:#666; font-size:14px;">Establishing secure handshake with Tripzo app.</p>
            </div>
            <script>
                var search = window.location.search.substring(1);
                var hash = window.location.hash.substring(1);
                var combined = (search ? search + "&" : "") + hash;
                var target = "tripzo://--/expo-auth-session?" + combined;
                setTimeout(function() {{ window.location.replace(target); }}, 100);
            </script>
            <style>@keyframes spin {{ 0% {{ transform: rotate(0deg); }} 100% {{ transform: rotate(360deg); }} }}</style>
        </body>
        </html>
    """)

@csrf_exempt
def facebook_proxy(request):
    return _get_proxy_html("facebook", request)

@csrf_exempt
def google_proxy(request):
    return _get_proxy_html("google", request)


class WalletView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        from .models import Wallet
        wallet, _ = Wallet.objects.get_or_create(user=request.user)
        return Response({"balance": wallet.balance})

class ReferralView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        user = request.user
        if not user.referral_code:
            import random, string
            user.referral_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
            user.save()
        referrals = user.referrals.all()
        return Response({
            "code": user.referral_code,
            "count": referrals.count(),
            "list": [{"id": r.id, "name": r.first_name, "joined": r.date_joined} for r in referrals]
        })

class RiderRideHistoryView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        from apps.rides.models import Ride
        rides = Ride.objects.filter(rider=request.user).order_by('-created_at')
        from apps.rides.serializers import RideSerializer
        serializer = RideSerializer(rides, many=True)
        return Response(serializer.data)

class CreateComplaintView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        from apps.supports.models import SupportTicket
        ride_id = request.data.get("ride_id")
        reason = request.data.get("reason")
        description = request.data.get("description", "")
        
        from apps.rides.models import Ride
        ride = Ride.objects.filter(id=ride_id).first() if ride_id else None
        
        ticket = SupportTicket.objects.create(
            user=request.user,
            ride=ride,
            reason=reason,
            description=description
        )
        return Response({"ticket_id": ticket.id, "status": ticket.status}, status=201)


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        old_password = request.data.get("old_password")
        new_password = request.data.get("new_password")
        if not old_password or not new_password:
            return Response({"error": "Both old and new passwords are required"}, status=400)
        
        user = request.user
        if not user.check_password(old_password):
            return Response({"error": "Incorrect old password"}, status=400)
        
        user.set_password(new_password)
        user.save()
        return Response({"status": "Password changed successfully"})

