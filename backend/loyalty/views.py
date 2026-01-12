import hashlib
import secrets
from decimal import Decimal
from uuid import uuid4
from datetime import timedelta
from django.conf import settings
from django.core.cache import cache
from django.core.mail import send_mail
from django.shortcuts import get_object_or_404
from django.db import models, transaction
from django.db.models import Sum
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import RefreshToken

from .models import (
    Tenant,
    OrganizationSettings,
    Location,
    User,
    StaffProfile,
    LoyaltyCard,
    OneTimeQR,
    LoyaltyRule,
    Offer,
    CouponAssignment,
    LoyaltyOperation,
    EmailVerificationCode,
    AuditLog,
)
from .serializers import (
    RegisterSerializer,
    LoginSerializer,
    EmailRequestSerializer,
    EmailConfirmSerializer,
    PhoneRequestSerializer,
    PhoneConfirmSerializer,
    QRValidateSerializer,
    PointsSerializer,
    RefundSerializer,
    POSPointsSerializer,
    PasswordChangeSerializer,
    UserSerializer,
    OperationSerializer,
    OfferSerializer,
    CouponAssignmentSerializer,
    LocationSerializer,
    LoyaltyRuleSerializer,
    OrganizationSettingsSerializer,
    StaffCreateSerializer,
)
from .permissions import IsTenantMember, IsClient, IsCashier, IsAdmin


def issue_tokens(user: User):
    refresh = RefreshToken.for_user(user)
    return {
        "access": str(refresh.access_token),
        "refresh": str(refresh),
    }


def hash_code(code: str) -> str:
    raw = f"{settings.SECRET_KEY}:{code}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def generate_code() -> str:
    return f"{secrets.randbelow(1000000):06d}"


def rate_limited(key: str, limit: int, window_seconds: int = 3600) -> bool:
    current = cache.get(key, 0)
    if current >= limit:
        return True
    if current == 0:
        cache.set(key, 1, timeout=window_seconds)
    else:
        cache.incr(key)
    return False


def audit_log(tenant: Tenant, user: User | None, action: str, metadata: dict | None = None):
    AuditLog.objects.create(tenant=tenant, user=user, action=action, metadata=metadata or {})


def send_email_code(user: User, code: str):
    subject = "Your Loyalty verification code"
    message = f"Your verification code is: {code}"
    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=False)


def mask_email(email: str) -> str:
    if "@" not in email:
        return email
    name, domain = email.split("@", 1)
    if len(name) <= 2:
        masked = "*" * len(name)
    else:
        masked = f"{name[0]}***{name[-1]}"
    return f"{masked}@{domain}"


def mask_phone(phone: str) -> str:
    if len(phone) < 4:
        return "***"
    return f"***{phone[-4:]}"


def get_rule(tenant: Tenant, location: Location | None) -> LoyaltyRule:
    if location:
        rule = LoyaltyRule.objects.filter(tenant=tenant, location=location).first()
        if rule:
            return rule
    rule = LoyaltyRule.objects.filter(tenant=tenant, location__isnull=True).first()
    if not rule:
        rule = LoyaltyRule.objects.create(tenant=tenant, earn_percent=Decimal("3.0"))
    return rule


def apply_rounding(value: Decimal, mode: str) -> int:
    if mode == LoyaltyRule.Rounding.CEIL:
        return int(value.to_integral_value(rounding="ROUND_CEILING"))
    if mode == LoyaltyRule.Rounding.ROUND:
        return int(value.to_integral_value(rounding="ROUND_HALF_UP"))
    return int(value.to_integral_value(rounding="ROUND_FLOOR"))


def update_tier(card: LoyaltyCard, rule: LoyaltyRule):
    points = card.current_points
    if points >= rule.gold_threshold:
        card.tier = "Gold"
    elif points >= rule.silver_threshold:
        card.tier = "Silver"
    else:
        card.tier = "Bronze"


def validate_qr(token: str) -> tuple[OneTimeQR | None, str | None]:
    qr = OneTimeQR.objects.select_related("card", "card__user").filter(token=token).first()
    if not qr:
        return None, "QR_NOT_FOUND"
    if qr.expires_at < timezone.now():
        return None, "QR_EXPIRED"
    if qr.used_at:
        return None, "QR_USED"
    if qr.card.status != LoyaltyCard.Status.ACTIVE:
        return None, "CARD_BLOCKED"
    return qr, None


def ops_limit_reached(card: LoyaltyCard, staff: User | None) -> tuple[bool, str | None]:
    max_earn = settings.MAX_EARN_PER_DAY_PER_CARD
    if max_earn:
        today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        earned = (
            LoyaltyOperation.objects.filter(
                card=card,
                type=LoyaltyOperation.Type.EARN,
                status=LoyaltyOperation.Status.SUCCESS,
                created_at__gte=today_start,
            ).aggregate(total=Sum("points"))["total"]
            or 0
        )
        if earned >= max_earn:
            return True, "MAX_EARN_PER_DAY_REACHED"
    if staff:
        max_ops = settings.MAX_OPS_PER_HOUR_PER_STAFF
        if max_ops:
            hour_ago = timezone.now() - timedelta(hours=1)
            ops_count = LoyaltyOperation.objects.filter(staff=staff, created_at__gte=hour_ago).count()
            if ops_count >= max_ops:
                return True, "MAX_OPS_PER_HOUR_REACHED"
    return False, None


class TenantMixin:
    def get_tenant(self) -> Tenant:
        slug = self.kwargs.get("tenant_slug")
        return get_object_or_404(Tenant, slug=slug)


def location_for_tenant(tenant: Tenant, location_id: int | None):
    if not location_id:
        return None
    return Location.objects.filter(id=location_id, tenant=tenant).first()


class RegisterView(TenantMixin, APIView):
    permission_classes = [AllowAny]

    def post(self, request, tenant_slug):
        tenant = self.get_tenant()
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"].lower()
        password = serializer.validated_data["password"]
        if User.objects.filter(tenant=tenant, email=email).exists():
            return Response({"detail": "EMAIL_EXISTS"}, status=status.HTTP_400_BAD_REQUEST)
        user = User.objects.create_user(email=email, password=password, tenant=tenant, role=User.Role.CLIENT)
        LoyaltyCard.objects.create(user=user, tenant=tenant)
        code = generate_code()
        EmailVerificationCode.objects.create(
            user=user,
            code_hash=hash_code(code),
            expires_at=timezone.now() + timedelta(minutes=10),
        )
        send_email_code(user, code)
        audit_log(tenant, user, "register", {"email": email})
        return Response({"detail": "EMAIL_VERIFICATION_SENT"})


class LoginView(TenantMixin, APIView):
    permission_classes = [AllowAny]

    def post(self, request, tenant_slug):
        tenant = self.get_tenant()
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"].lower()
        password = serializer.validated_data["password"]
        rate_key = f"rl:login:{tenant.id}:{email}"
        if rate_limited(rate_key, 20):
            return Response({"detail": "RATE_LIMIT"}, status=status.HTTP_429_TOO_MANY_REQUESTS)
        user = User.objects.filter(tenant=tenant, email=email).first()
        if not user or not user.check_password(password):
            return Response({"detail": "INVALID_CREDENTIALS"}, status=status.HTTP_401_UNAUTHORIZED)
        if not user.email_verified:
            return Response({"detail": "EMAIL_NOT_VERIFIED"}, status=status.HTTP_403_FORBIDDEN)
        tokens = issue_tokens(user)
        audit_log(tenant, user, "login", {})
        return Response({"tokens": tokens, "user": UserSerializer(user).data})


class EmailRequestCodeView(TenantMixin, APIView):
    permission_classes = [AllowAny]

    def post(self, request, tenant_slug):
        tenant = self.get_tenant()
        serializer = EmailRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"].lower()
        rate_key = f"rl:email:{tenant.id}:{email}"
        if rate_limited(rate_key, settings.EMAIL_CODE_RATE_LIMIT_PER_HOUR):
            return Response({"detail": "RATE_LIMIT"}, status=status.HTTP_429_TOO_MANY_REQUESTS)
        user = User.objects.filter(tenant=tenant, email=email).first()
        if not user:
            return Response({"detail": "USER_NOT_FOUND"}, status=status.HTTP_404_NOT_FOUND)
        code = generate_code()
        EmailVerificationCode.objects.create(
            user=user,
            code_hash=hash_code(code),
            expires_at=timezone.now() + timedelta(minutes=10),
        )
        send_email_code(user, code)
        audit_log(tenant, user, "email_code_requested", {})
        return Response({"detail": "EMAIL_CODE_SENT"})


class EmailConfirmView(TenantMixin, APIView):
    permission_classes = [AllowAny]

    def post(self, request, tenant_slug):
        tenant = self.get_tenant()
        serializer = EmailConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"].lower()
        code = serializer.validated_data["code"]
        user = User.objects.filter(tenant=tenant, email=email).first()
        if not user:
            return Response({"detail": "USER_NOT_FOUND"}, status=status.HTTP_404_NOT_FOUND)
        record = EmailVerificationCode.objects.filter(user=user).order_by("-requested_at").first()
        if not record:
            return Response({"detail": "CODE_NOT_FOUND"}, status=status.HTTP_400_BAD_REQUEST)
        record.attempts += 1
        record.save()
        if timezone.now() > record.expires_at:
            return Response({"detail": "CODE_EXPIRED"}, status=status.HTTP_400_BAD_REQUEST)
        if record.code_hash != hash_code(code):
            return Response({"detail": "CODE_INVALID"}, status=status.HTTP_400_BAD_REQUEST)
        user.email_verified = True
        user.save()
        audit_log(tenant, user, "email_verified", {})
        return Response({"detail": "EMAIL_VERIFIED"})


class PhoneRequestView(TenantMixin, APIView):
    permission_classes = [IsTenantMember, IsClient]

    def post(self, request, tenant_slug):
        serializer = PhoneRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        rate_key = f"rl:phone:{request.user.id}"
        if rate_limited(rate_key, settings.OTP_RATE_LIMIT_PER_HOUR):
            return Response({"detail": "RATE_LIMIT"}, status=status.HTTP_429_TOO_MANY_REQUESTS)
        request.user.phone = serializer.validated_data["phone"]
        code = generate_code()
        request.user.otp_hash = hash_code(code)
        request.user.otp_expires_at = timezone.now() + timedelta(minutes=5)
        request.user.otp_requested_at = timezone.now()
        request.user.otp_attempts = 0
        request.user.save()
        payload = {"detail": "OTP_SENT"}
        if settings.DEBUG:
            payload["otp"] = code
            print(f"[OTP] {request.user.email} -> {code}")
        return Response(payload)


class PhoneConfirmView(TenantMixin, APIView):
    permission_classes = [IsTenantMember, IsClient]

    def post(self, request, tenant_slug):
        serializer = PhoneConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        code = serializer.validated_data["code"]
        request.user.otp_attempts += 1
        request.user.save()
        if not request.user.otp_is_valid(hash_code(code)):
            return Response({"detail": "OTP_INVALID"}, status=status.HTTP_400_BAD_REQUEST)
        request.user.phone_verified = True
        request.user.otp_hash = ""
        request.user.otp_expires_at = None
        request.user.save()
        return Response({"detail": "PHONE_VERIFIED"})


class ClientMeView(TenantMixin, APIView):
    permission_classes = [IsTenantMember, IsClient]

    def get(self, request, tenant_slug):
        card = request.user.card
        data = UserSerializer(request.user).data
        data["current_points"] = card.current_points
        data["tier"] = card.tier
        return Response(data)


class ClientOperationsView(TenantMixin, APIView):
    permission_classes = [IsTenantMember, IsClient]

    def get(self, request, tenant_slug):
        ops = request.user.card.operations.order_by("-created_at")
        op_type = request.query_params.get("type")
        if op_type:
            ops = ops.filter(type=op_type)
        receipt_id = request.query_params.get("receipt_id")
        if receipt_id:
            ops = ops.filter(receipt_id__icontains=receipt_id)
        date_from = request.query_params.get("from")
        date_to = request.query_params.get("to")
        if date_from:
            ops = ops.filter(created_at__gte=date_from)
        if date_to:
            ops = ops.filter(created_at__lte=date_to)
        ops = ops[:100]
        return Response(OperationSerializer(ops, many=True).data)


class ClientOffersView(TenantMixin, APIView):
    permission_classes = [IsTenantMember, IsClient]

    def get(self, request, tenant_slug):
        now = timezone.now()
        offers = Offer.objects.filter(tenant=request.user.tenant, is_active=True).filter(
            models.Q(active_from__isnull=True) | models.Q(active_from__lte=now),
            models.Q(active_to__isnull=True) | models.Q(active_to__gte=now),
        )
        return Response(OfferSerializer(offers, many=True).data)


class ClientCouponsView(TenantMixin, APIView):
    permission_classes = [IsTenantMember, IsClient]

    def get(self, request, tenant_slug):
        assignments = CouponAssignment.objects.filter(card=request.user.card).order_by("-created_at")
        return Response(CouponAssignmentSerializer(assignments, many=True).data)


class ClientQRIssueView(TenantMixin, APIView):
    permission_classes = [IsTenantMember, IsClient]

    def post(self, request, tenant_slug):
        if not request.user.phone_verified:
            return Response({"detail": "PHONE_NOT_VERIFIED"}, status=status.HTTP_400_BAD_REQUEST)
        if not request.user.email_verified:
            return Response({"detail": "EMAIL_NOT_VERIFIED"}, status=status.HTTP_400_BAD_REQUEST)
        token = uuid4().hex
        expires_at = timezone.now() + timedelta(seconds=10)
        OneTimeQR.objects.create(card=request.user.card, token=token, expires_at=expires_at)
        return Response({"qr_payload": token, "expires_at": expires_at.isoformat()})


class ClientPasswordChangeView(TenantMixin, APIView):
    permission_classes = [IsTenantMember, IsClient]

    def post(self, request, tenant_slug):
        serializer = PasswordChangeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if not request.user.check_password(serializer.validated_data["current_password"]):
            return Response({"detail": "INVALID_PASSWORD"}, status=status.HTTP_400_BAD_REQUEST)
        request.user.set_password(serializer.validated_data["new_password"])
        request.user.save()
        audit_log(request.user.tenant, request.user, "password_change", {})
        return Response({"detail": "PASSWORD_CHANGED"})


class LoyaltyQRValidateView(TenantMixin, APIView):
    permission_classes = [IsTenantMember, IsCashier]

    def post(self, request, tenant_slug):
        serializer = QRValidateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token = serializer.validated_data["qr_payload"]
        qr, error = validate_qr(token)
        if error:
            return Response({"detail": error}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            {
                "card_id": qr.card_id,
                "client_email": mask_email(qr.card.user.email),
                "client_phone": mask_phone(qr.card.user.phone),
                "tier": qr.card.tier,
                "current_points": qr.card.current_points,
            }
        )


class LoyaltyEarnView(TenantMixin, APIView):
    permission_classes = [IsTenantMember, IsCashier]

    def post(self, request, tenant_slug):
        return handle_points(request, tenant_slug, LoyaltyOperation.Type.EARN, LoyaltyOperation.Source.CASHIER_APP)


class LoyaltyRedeemView(TenantMixin, APIView):
    permission_classes = [IsTenantMember, IsCashier]

    def post(self, request, tenant_slug):
        return handle_points(request, tenant_slug, LoyaltyOperation.Type.REDEEM, LoyaltyOperation.Source.CASHIER_APP)


class LoyaltyRefundView(TenantMixin, APIView):
    permission_classes = [IsTenantMember, IsCashier]

    def post(self, request, tenant_slug):
        tenant = self.get_tenant()
        serializer = RefundSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        receipt_id = serializer.validated_data["receipt_id"]
        idempotency_key = serializer.validated_data["idempotency_key"]
        existing = LoyaltyOperation.objects.filter(tenant=tenant, idempotency_key=idempotency_key).first()
        if existing:
            return Response({"detail": "OK", "points": existing.points, "current_points": existing.card.current_points})
        original = LoyaltyOperation.objects.filter(
            tenant=tenant,
            receipt_id=receipt_id,
            type__in=[LoyaltyOperation.Type.EARN, LoyaltyOperation.Type.REDEEM],
            status=LoyaltyOperation.Status.SUCCESS,
        ).order_by("-created_at").first()
        if not original:
            return Response({"detail": "RECEIPT_NOT_FOUND"}, status=status.HTTP_404_NOT_FOUND)
        if LoyaltyOperation.objects.filter(original_operation=original, type=LoyaltyOperation.Type.REFUND).exists():
            return Response({"detail": "ALREADY_REFUNDED"}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            card = LoyaltyCard.objects.select_for_update().get(id=original.card_id)
            points = original.points
            if original.type == LoyaltyOperation.Type.EARN:
                if card.current_points < points:
                    return Response({"detail": "INSUFFICIENT_POINTS"}, status=status.HTTP_400_BAD_REQUEST)
                card.current_points -= points
            else:
                card.current_points += points
            rule = get_rule(tenant, original.location)
            update_tier(card, rule)
            card.save()
            LoyaltyOperation.objects.create(
                tenant=tenant,
                card=card,
                type=LoyaltyOperation.Type.REFUND,
                source=LoyaltyOperation.Source.CASHIER_APP,
                amount=original.amount,
                points=points,
                receipt_id=receipt_id,
                idempotency_key=idempotency_key,
                original_operation=original,
                staff=request.user,
                location=original.location,
                status=LoyaltyOperation.Status.SUCCESS,
                metadata={"refunded_type": original.type},
            )
            audit_log(tenant, request.user, "refund", {"receipt_id": receipt_id})
            return Response({"detail": "OK", "points": points, "current_points": card.current_points})


class POSLoyaltyEarnView(TenantMixin, APIView):
    permission_classes = [AllowAny]

    def post(self, request, tenant_slug):
        tenant = self.get_tenant()
        api_key = request.headers.get("X-POS-API-KEY")
        if not api_key:
            return Response({"detail": "MISSING_API_KEY"}, status=status.HTTP_401_UNAUTHORIZED)
        serializer = POSPointsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        location = location_for_tenant(tenant, serializer.validated_data["location_id"])
        if not location:
            return Response({"detail": "LOCATION_NOT_FOUND"}, status=status.HTTP_400_BAD_REQUEST)
        if api_key not in (tenant.pos_api_key, location.pos_api_key):
            return Response({"detail": "INVALID_API_KEY"}, status=status.HTTP_401_UNAUTHORIZED)
        receipt_id = serializer.validated_data["receipt_id"]
        existing = LoyaltyOperation.objects.filter(
            tenant=tenant,
            receipt_id=receipt_id,
            source=LoyaltyOperation.Source.POS,
        ).first()
        if existing:
            return Response({"detail": "OK", "points": existing.points, "current_points": existing.card.current_points})
        return handle_points(
            request,
            tenant_slug,
            LoyaltyOperation.Type.EARN,
            LoyaltyOperation.Source.POS,
            receipt_id=receipt_id,
            location=location,
            pos_payload=serializer.validated_data,
        )


class CashierOperationsView(TenantMixin, APIView):
    permission_classes = [IsTenantMember, IsCashier]

    def get(self, request, tenant_slug):
        ops = LoyaltyOperation.objects.filter(tenant=request.user.tenant).order_by("-created_at")
        receipt_id = request.query_params.get("receipt_id")
        if receipt_id:
            ops = ops.filter(receipt_id__icontains=receipt_id)
        ops = ops[:100]
        return Response(OperationSerializer(ops, many=True).data)


class AdminDashboardView(TenantMixin, APIView):
    permission_classes = [IsTenantMember, IsAdmin]

    def get(self, request, tenant_slug):
        tenant = request.user.tenant
        return Response(
            {
                "clients": User.objects.filter(tenant=tenant, role=User.Role.CLIENT).count(),
                "staff": User.objects.filter(tenant=tenant, role__in=[User.Role.ADMIN, User.Role.CASHIER]).count(),
                "locations": Location.objects.filter(tenant=tenant).count(),
                "operations": LoyaltyOperation.objects.filter(tenant=tenant).count(),
            }
        )


class AdminCustomersView(TenantMixin, APIView):
    permission_classes = [IsTenantMember, IsAdmin]

    def get(self, request, tenant_slug):
        users = User.objects.filter(tenant=request.user.tenant, role=User.Role.CLIENT).order_by("-id")[:200]
        data = []
        for user in users:
            card = getattr(user, "card", None)
            data.append(
                {
                    "id": user.id,
                    "email": user.email,
                    "phone": user.phone,
                    "tier": card.tier if card else "-",
                    "points": card.current_points if card else 0,
                    "email_verified": user.email_verified,
                    "phone_verified": user.phone_verified,
                }
            )
        return Response(data)


class AdminStaffView(TenantMixin, APIView):
    permission_classes = [IsTenantMember, IsAdmin]

    def get(self, request, tenant_slug):
        users = User.objects.filter(tenant=request.user.tenant, role__in=[User.Role.ADMIN, User.Role.CASHIER])
        data = []
        for user in users:
            staff = getattr(user, "staff_profile", None)
            data.append(
                {
                    "id": user.id,
                    "email": user.email,
                    "role": user.role,
                    "location": staff.location.name if staff and staff.location else "-",
                    "active": staff.is_active if staff else True,
                }
            )
        return Response(data)

    def post(self, request, tenant_slug):
        tenant = request.user.tenant
        serializer = StaffCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"].lower()
        password = serializer.validated_data["password"]
        role = serializer.validated_data["role"]
        location = location_for_tenant(tenant, serializer.validated_data.get("location_id"))
        if User.objects.filter(tenant=tenant, email=email).exists():
            return Response({"detail": "EMAIL_EXISTS"}, status=status.HTTP_400_BAD_REQUEST)
        user = User.objects.create_user(
            email=email,
            password=password,
            tenant=tenant,
            role=role,
            email_verified=True,
        )
        StaffProfile.objects.create(user=user, location=location)
        return Response({"detail": "CREATED"}, status=status.HTTP_201_CREATED)


class AdminLocationsView(TenantMixin, APIView):
    permission_classes = [IsTenantMember, IsAdmin]

    def get(self, request, tenant_slug):
        locations = Location.objects.filter(tenant=request.user.tenant).order_by("id")
        return Response(LocationSerializer(locations, many=True).data)

    def post(self, request, tenant_slug):
        serializer = LocationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        location = Location.objects.create(tenant=request.user.tenant, **serializer.validated_data)
        return Response(LocationSerializer(location).data, status=status.HTTP_201_CREATED)


class AdminRulesView(TenantMixin, APIView):
    permission_classes = [IsTenantMember, IsAdmin]

    def get(self, request, tenant_slug):
        rules = LoyaltyRule.objects.filter(tenant=request.user.tenant)
        return Response(LoyaltyRuleSerializer(rules, many=True).data)

    def post(self, request, tenant_slug):
        serializer = LoyaltyRuleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        location = serializer.validated_data.get("location")
        rule, _ = LoyaltyRule.objects.update_or_create(
            tenant=request.user.tenant,
            location=location,
            defaults=serializer.validated_data,
        )
        return Response(LoyaltyRuleSerializer(rule).data)


class AdminOperationsView(TenantMixin, APIView):
    permission_classes = [IsTenantMember, IsAdmin]

    def get(self, request, tenant_slug):
        ops = LoyaltyOperation.objects.filter(tenant=request.user.tenant).order_by("-created_at")
        receipt_id = request.query_params.get("receipt_id")
        if receipt_id:
            ops = ops.filter(receipt_id__icontains=receipt_id)
        return Response(OperationSerializer(ops[:200], many=True).data)


class AdminOffersView(TenantMixin, APIView):
    permission_classes = [IsTenantMember, IsAdmin]

    def get(self, request, tenant_slug):
        offers = Offer.objects.filter(tenant=request.user.tenant).order_by("-id")
        return Response(OfferSerializer(offers, many=True).data)

    def post(self, request, tenant_slug):
        serializer = OfferSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        offer = Offer.objects.create(tenant=request.user.tenant, **serializer.validated_data)
        return Response(OfferSerializer(offer).data, status=status.HTTP_201_CREATED)


class AdminSettingsView(TenantMixin, APIView):
    permission_classes = [IsTenantMember, IsAdmin]

    def get(self, request, tenant_slug):
        settings_obj, _ = OrganizationSettings.objects.get_or_create(tenant=request.user.tenant)
        return Response(OrganizationSettingsSerializer(settings_obj).data)

    def post(self, request, tenant_slug):
        settings_obj, _ = OrganizationSettings.objects.get_or_create(tenant=request.user.tenant)
        serializer = OrganizationSettingsSerializer(settings_obj, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


def handle_points(
    request,
    tenant_slug,
    op_type,
    source,
    receipt_id=None,
    location=None,
    pos_payload=None,
):
    tenant = Tenant.objects.get(slug=tenant_slug)
    if source == LoyaltyOperation.Source.POS:
        serializer = POSPointsSerializer(data=pos_payload)
    else:
        serializer = PointsSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    data = serializer.validated_data
    token = data["qr_payload"]
    amount = data["amount"]
    idempotency_key = data.get("idempotency_key")
    receipt_id = receipt_id or data.get("receipt_id")

    if source != LoyaltyOperation.Source.POS and not idempotency_key:
        return Response({"detail": "IDEMPOTENCY_REQUIRED"}, status=status.HTTP_400_BAD_REQUEST)

    existing = None
    if idempotency_key:
        existing = LoyaltyOperation.objects.filter(tenant=tenant, idempotency_key=idempotency_key).first()
    if existing:
        return Response({"detail": "OK", "points": existing.points, "current_points": existing.card.current_points})

    location = location or location_for_tenant(tenant, data.get("location_id"))
    if data.get("location_id") and not location:
        return Response({"detail": "LOCATION_NOT_FOUND"}, status=status.HTTP_400_BAD_REQUEST)

    with transaction.atomic():
        qr = OneTimeQR.objects.select_for_update().select_related("card", "card__user").filter(token=token).first()
        if not qr:
            return Response({"detail": "QR_NOT_FOUND"}, status=status.HTTP_400_BAD_REQUEST)
        if qr.expires_at < timezone.now():
            return Response({"detail": "QR_EXPIRED"}, status=status.HTTP_400_BAD_REQUEST)
        if qr.used_at:
            return Response({"detail": "QR_USED"}, status=status.HTTP_400_BAD_REQUEST)
        if qr.card.status != LoyaltyCard.Status.ACTIVE:
            return Response({"detail": "CARD_BLOCKED"}, status=status.HTTP_400_BAD_REQUEST)

        card = LoyaltyCard.objects.select_for_update().get(id=qr.card_id)

        limit_hit, reason = ops_limit_reached(card, request.user if source != LoyaltyOperation.Source.POS else None)
        if limit_hit:
            LoyaltyOperation.objects.create(
                tenant=tenant,
                card=card,
                type=op_type,
                source=source,
                amount=amount,
                points=0,
                receipt_id=receipt_id,
                idempotency_key=idempotency_key,
                staff=request.user if source != LoyaltyOperation.Source.POS else None,
                location=location,
                status=LoyaltyOperation.Status.FAILED,
                fail_reason=reason,
            )
            return Response({"detail": reason}, status=status.HTTP_400_BAD_REQUEST)

        rule = get_rule(tenant, location)
        if op_type == LoyaltyOperation.Type.EARN:
            if Decimal(amount) < rule.min_amount:
                return Response({"detail": "MIN_AMOUNT_NOT_MET"}, status=status.HTTP_400_BAD_REQUEST)
            raw_points = Decimal(amount) * rule.earn_percent / Decimal("100")
            points = apply_rounding(raw_points, rule.rounding_mode)
            card.current_points += points
        else:
            points = int(Decimal(amount).to_integral_value(rounding="ROUND_FLOOR"))
            if card.current_points < points:
                LoyaltyOperation.objects.create(
                    tenant=tenant,
                    card=card,
                    type=op_type,
                    source=source,
                    amount=amount,
                    points=0,
                    receipt_id=receipt_id,
                    idempotency_key=idempotency_key,
                    staff=request.user if source != LoyaltyOperation.Source.POS else None,
                    location=location,
                    status=LoyaltyOperation.Status.FAILED,
                    fail_reason="INSUFFICIENT_POINTS",
                )
                return Response({"detail": "INSUFFICIENT_POINTS"}, status=status.HTTP_400_BAD_REQUEST)
            card.current_points -= points

        update_tier(card, rule)
        card.save()
        qr.used_at = timezone.now()
        qr.save()

        LoyaltyOperation.objects.create(
            tenant=tenant,
            card=card,
            type=op_type,
            source=source,
            amount=amount,
            points=points,
            receipt_id=receipt_id,
            idempotency_key=idempotency_key,
            staff=request.user if source != LoyaltyOperation.Source.POS else None,
            location=location,
            status=LoyaltyOperation.Status.SUCCESS,
        )
        audit_log(tenant, request.user if source != LoyaltyOperation.Source.POS else None, op_type.lower(), {})
        return Response({"detail": "OK", "points": points, "current_points": card.current_points})
