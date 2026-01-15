import hashlib
import secrets
from decimal import Decimal
from uuid import uuid4
from datetime import timedelta, datetime
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
    RuleTarget,
    Offer,
    OfferTarget,
    OfferRedemption,
    CouponAssignment,
    LoyaltyOperation,
    EmailVerificationCode,
    OneTimeCode,
    AuditLog,
)
from .serializers import (
    RegisterSerializer,
    LoginSerializer,
    EmailRequestSerializer,
    EmailConfirmSerializer,
    PhoneRequestSerializer,
    PhoneConfirmSerializer,
    TelegramStartSerializer,
    TelegramVerifySerializer,
    QRValidateSerializer,
    PointsSerializer,
    RefundSerializer,
    POSPointsSerializer,
    PasswordChangeSerializer,
    UserSerializer,
    OperationSerializer,
    OfferSerializer,
    OfferUseSerializer,
    CouponAssignmentSerializer,
    LocationSerializer,
    LoyaltyRuleSerializer,
    OrganizationSettingsSerializer,
    StaffCreateSerializer,
)
from .permissions import IsTenantMember, IsClient, IsCashier, IsAdmin
from .telegram_auth import (
    cache_tenant_slug,
    get_cached_tenant_slug,
    hash_otp,
    issue_telegram_code,
    normalize_phone,
    send_telegram_message,
)


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
    subject = "Код подтверждения"
    message = f"Ваш код: {code}. Он действует {settings.EMAIL_CODE_TTL_MINUTES} минут."
    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=False)


def invalidate_email_codes(user: User):
    EmailVerificationCode.objects.filter(user=user, tenant=user.tenant, is_used=False).update(is_used=True)


def can_resend_email_code(user: User, now: datetime) -> bool:
    latest = EmailVerificationCode.objects.filter(user=user, tenant=user.tenant).order_by("-last_sent_at", "-created_at").first()
    if not latest or not latest.last_sent_at:
        return True
    elapsed = (now - latest.last_sent_at).total_seconds()
    return elapsed >= settings.EMAIL_CODE_RESEND_SECONDS


def create_email_code(user: User, now: datetime):
    code = generate_code()
    record = EmailVerificationCode.objects.create(
        user=user,
        tenant=user.tenant,
        code=code,
        expires_at=now + timedelta(minutes=settings.EMAIL_CODE_TTL_MINUTES),
        last_sent_at=now,
    )
    send_email_code(user, code)
    return record


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


def get_rule(tenant: Tenant, location: Location | None, user: User | None) -> LoyaltyRule:
    if user:
        targeted = (
            LoyaltyRule.objects.filter(tenant=tenant, targets__user=user)
            .order_by("-id")
            .first()
        )
        if targeted:
            return targeted
    if location:
        rule = (
            LoyaltyRule.objects.filter(tenant=tenant, location=location, applies_to_all=True)
            .order_by("-id")
            .first()
        )
        if rule:
            return rule
    rule = (
        LoyaltyRule.objects.filter(tenant=tenant, location__isnull=True, applies_to_all=True)
        .order_by("-id")
        .first()
    )
    if not rule:
        rule = LoyaltyRule.objects.create(tenant=tenant, earn_percent=Decimal("3.0"), applies_to_all=True)
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


def validate_qr(tenant: Tenant, token: str) -> tuple[OneTimeQR | None, str | None]:
    qr = OneTimeQR.objects.select_related("card", "card__user").filter(tenant=tenant, token=token).first()
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
        tenant = getattr(self.request, "tenant", None)
        if tenant:
            return tenant
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
        first_name = serializer.validated_data["first_name"]
        last_name = serializer.validated_data["last_name"]
        password = serializer.validated_data["password"]
        if User.objects.filter(tenant=tenant, email=email).exists():
            return Response({"detail": "EMAIL_EXISTS"}, status=status.HTTP_400_BAD_REQUEST)
        user = User.objects.create_user(
            email=email,
            password=password,
            tenant=tenant,
            role=User.Role.CLIENT,
            is_active=False,
            email_verified=False,
            first_name=first_name,
            last_name=last_name,
        )
        LoyaltyCard.objects.create(user=user, tenant=tenant)
        invalidate_email_codes(user)
        create_email_code(user, timezone.now())
        audit_log(tenant, user, "register", {"email": email})
        return Response({"detail": "Код отправлен на почту"}, status=status.HTTP_201_CREATED)


def handle_login(request, tenant_slug, allowed_roles: list[str]):
    tenant = getattr(request, "tenant", None) or get_object_or_404(Tenant, slug=tenant_slug)
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
    if allowed_roles and user.role not in allowed_roles:
        return Response({"detail": "ROLE_NOT_ALLOWED"}, status=status.HTTP_403_FORBIDDEN)
    if not user.is_active or not user.email_verified:
        now = timezone.now()
        if not user.email_verified and can_resend_email_code(user, now):
            invalidate_email_codes(user)
            create_email_code(user, now)
        return Response(
            {"detail": "EMAIL_NOT_VERIFIED", "message": "EMAIL_NOT_VERIFIED"},
            status=status.HTTP_403_FORBIDDEN,
        )
    tokens = issue_tokens(user)
    audit_log(tenant, user, "login", {})
    return Response({"tokens": tokens, "user": UserSerializer(user).data})


class LoginView(TenantMixin, APIView):
    permission_classes = [AllowAny]

    def post(self, request, tenant_slug):
        return handle_login(request, tenant_slug, allowed_roles=[User.Role.CLIENT])


class ClientLoginView(TenantMixin, APIView):
    permission_classes = [AllowAny]

    def post(self, request, tenant_slug):
        return handle_login(request, tenant_slug, allowed_roles=[User.Role.CLIENT])


class CashierLoginView(TenantMixin, APIView):
    permission_classes = [AllowAny]

    def post(self, request, tenant_slug):
        return handle_login(request, tenant_slug, allowed_roles=[User.Role.CASHIER])


class AdminLoginView(TenantMixin, APIView):
    permission_classes = [AllowAny]

    def post(self, request, tenant_slug):
        return handle_login(request, tenant_slug, allowed_roles=[User.Role.ADMIN])


class AuthMeView(TenantMixin, APIView):
    permission_classes = [IsTenantMember]

    def get(self, request, tenant_slug):
        return Response(UserSerializer(request.user).data)


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
        if not user or user.email_verified:
            return Response({"detail": "Код отправлен на почту"})
        now = timezone.now()
        if not can_resend_email_code(user, now):
            return Response({"detail": "RESEND_TOO_SOON"}, status=status.HTTP_429_TOO_MANY_REQUESTS)
        invalidate_email_codes(user)
        create_email_code(user, now)
        audit_log(tenant, user, "email_code_requested", {})
        return Response({"detail": "Код отправлен на почту"})


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
            return Response({"detail": "CODE_INVALID"}, status=status.HTTP_400_BAD_REQUEST)
        record = EmailVerificationCode.objects.filter(user=user, tenant=tenant, is_used=False).order_by("-created_at").first()
        if not record:
            return Response({"detail": "CODE_INVALID"}, status=status.HTTP_400_BAD_REQUEST)
        now = timezone.now()
        if record.expires_at < now:
            record.is_used = True
            record.save(update_fields=["is_used"])
            return Response({"detail": "CODE_EXPIRED"}, status=status.HTTP_400_BAD_REQUEST)
        if record.attempts >= settings.EMAIL_CODE_MAX_ATTEMPTS:
            record.is_used = True
            record.save(update_fields=["is_used"])
            return Response({"detail": "CODE_ATTEMPTS_EXCEEDED"}, status=status.HTTP_429_TOO_MANY_REQUESTS)
        if record.code != code:
            record.attempts += 1
            if record.attempts >= settings.EMAIL_CODE_MAX_ATTEMPTS:
                record.is_used = True
            record.save(update_fields=["attempts", "is_used"])
            return Response({"detail": "CODE_INVALID"}, status=status.HTTP_400_BAD_REQUEST)
        user.email_verified = True
        user.is_active = True
        user.save(update_fields=["email_verified", "is_active"])
        record.is_used = True
        record.save(update_fields=["is_used"])
        audit_log(tenant, user, "email_verified", {})
        tokens = issue_tokens(user)
        return Response(
            {
                "detail": "EMAIL_VERIFIED",
                "tokens": tokens,
                "user": UserSerializer(user).data,
            }
        )


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


class TelegramStartView(TenantMixin, APIView):
    permission_classes = [AllowAny]

    def post(self, request, tenant_slug):
        serializer = TelegramStartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        tenant = self.get_tenant()
        phone = normalize_phone(serializer.validated_data["phone"])
        if not phone:
            return Response({"detail": "PHONE_REQUIRED"}, status=status.HTTP_400_BAD_REQUEST)
        rate_key = f"rl:telegram:start:{tenant.id}:{phone}"
        if rate_limited(rate_key, settings.TELEGRAM_CODE_RATE_LIMIT_PER_HOUR):
            return Response({"detail": "RATE_LIMIT"}, status=status.HTTP_429_TOO_MANY_REQUESTS)
        return Response({"detail": "OK", "expires_in": settings.OTP_TTL_SECONDS})


class TelegramVerifyView(TenantMixin, APIView):
    permission_classes = [AllowAny]

    def post(self, request, tenant_slug):
        serializer = TelegramVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        tenant = self.get_tenant()
        phone = normalize_phone(serializer.validated_data["phone"])
        if not phone:
            return Response({"detail": "PHONE_REQUIRED"}, status=status.HTTP_400_BAD_REQUEST)
        code = serializer.validated_data["code"]
        rate_key = f"rl:telegram:verify:{tenant.id}:{phone}"
        if rate_limited(rate_key, settings.TELEGRAM_VERIFY_RATE_LIMIT_PER_HOUR):
            return Response({"detail": "RATE_LIMIT"}, status=status.HTTP_429_TOO_MANY_REQUESTS)

        now = timezone.now()
        record = (
            OneTimeCode.objects.filter(
                tenant=tenant,
                purpose=OneTimeCode.Purpose.TELEGRAM_PHONE_LOGIN,
                recipient=phone,
                consumed_at__isnull=True,
                expires_at__gte=now,
            )
            .order_by("-created_at")
            .first()
        )
        if not record:
            return Response({"detail": "CODE_INVALID"}, status=status.HTTP_400_BAD_REQUEST)
        if record.attempts >= settings.OTP_MAX_ATTEMPTS:
            record.consumed_at = now
            record.save(update_fields=["consumed_at"])
            return Response({"detail": "CODE_ATTEMPTS_EXCEEDED"}, status=status.HTTP_429_TOO_MANY_REQUESTS)
        if record.code_hash != hash_otp(code, record.purpose, phone):
            record.attempts += 1
            if record.attempts >= settings.OTP_MAX_ATTEMPTS:
                record.consumed_at = now
                record.save(update_fields=["attempts", "consumed_at"])
                return Response({"detail": "CODE_ATTEMPTS_EXCEEDED"}, status=status.HTTP_429_TOO_MANY_REQUESTS)
            record.save(update_fields=["attempts"])
            return Response({"detail": "CODE_INVALID"}, status=status.HTTP_400_BAD_REQUEST)

        record.consumed_at = now
        record.save(update_fields=["consumed_at"])

        user = User.objects.filter(tenant=tenant, phone=phone).first()
        if user and user.role != User.Role.CLIENT:
            return Response({"detail": "ROLE_NOT_ALLOWED"}, status=status.HTTP_403_FORBIDDEN)
        if not user:
            email_base = f"phone_{phone.strip('+')}@{tenant.slug}.local"
            email = email_base
            counter = 1
            while User.objects.filter(tenant=tenant, email=email).exists():
                email = f"phone_{phone.strip('+')}_{counter}@{tenant.slug}.local"
                counter += 1
            user = User.objects.create_user(
                email=email,
                password=None,
                tenant=tenant,
                role=User.Role.CLIENT,
                is_active=True,
                email_verified=False,
                phone=phone,
                phone_verified=True,
            )
            LoyaltyCard.objects.create(user=user, tenant=tenant)
        else:
            user.phone = phone
            user.phone_verified = True
            user.save(update_fields=["phone", "phone_verified"])

        tokens = issue_tokens(user)
        audit_log(tenant, user, "login_telegram", {"phone": phone})
        return Response({"tokens": tokens, "user": UserSerializer(user).data})


class TelegramWebhookView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
        if not settings.TELEGRAM_WEBHOOK_SECRET or secret != settings.TELEGRAM_WEBHOOK_SECRET:
            return Response({"detail": "FORBIDDEN"}, status=status.HTTP_403_FORBIDDEN)

        payload = request.data or {}
        message = payload.get("message") or {}
        chat = message.get("chat") or {}
        chat_id = chat.get("id")
        if not chat_id:
            return Response({"detail": "OK"})

        text = message.get("text", "")
        if text.startswith("/start"):
            parts = text.split(maxsplit=1)
            if len(parts) > 1:
                cache_tenant_slug(chat_id, parts[1].strip())
            return Response({"detail": "OK"})

        contact = message.get("contact")
        if not contact:
            return Response({"detail": "OK"})

        phone = contact.get("phone_number", "")
        normalized = normalize_phone(phone)
        if not normalized:
            try:
                send_telegram_message(chat_id, "Invalid phone number.")
            except RuntimeError:
                pass
            return Response({"detail": "OK"})
        tenant_slug = get_cached_tenant_slug(chat_id)
        if not tenant_slug:
            try:
                send_telegram_message(chat_id, "Open the bot from your tenant link and try again.")
            except RuntimeError:
                pass
            return Response({"detail": "OK"})

        tenant = Tenant.objects.filter(slug=tenant_slug).first()
        if not tenant:
            try:
                send_telegram_message(chat_id, "Tenant not found. Please check the link.")
            except RuntimeError:
                pass
            return Response({"detail": "OK"})

        rate_key_phone = f"rl:telegram:code:{tenant.id}:{normalized}"
        rate_key_chat = f"rl:telegram:chat:{tenant.id}:{chat_id}"
        if rate_limited(rate_key_phone, settings.TELEGRAM_CODE_RATE_LIMIT_PER_HOUR) or rate_limited(
            rate_key_chat, settings.TELEGRAM_CHAT_RATE_LIMIT_PER_HOUR
        ):
            try:
                send_telegram_message(chat_id, "Too many requests. Please try later.")
            except RuntimeError:
                pass
            return Response({"detail": "OK"})

        _, code = issue_telegram_code(tenant, normalized, chat_id=chat_id)
        try:
            send_telegram_message(chat_id, f"Your login code: {code}")
        except RuntimeError:
            pass
        return Response({"detail": "OK"})


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
        offers = offers.filter(
            models.Q(applies_to_all=True) | models.Q(targets__user=request.user)
        ).distinct()
        return Response(OfferSerializer(offers, many=True, context={"user": request.user}).data)


class ClientOfferUseView(TenantMixin, APIView):
    permission_classes = [IsTenantMember, IsClient]

    def post(self, request, tenant_slug):
        serializer = OfferUseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        offer_id = serializer.validated_data["offer_id"]
        now = timezone.now()
        offer = Offer.objects.filter(
            tenant=request.user.tenant,
            id=offer_id,
            is_active=True,
        ).filter(
            models.Q(active_from__isnull=True) | models.Q(active_from__lte=now),
            models.Q(active_to__isnull=True) | models.Q(active_to__gte=now),
        ).first()
        if not offer:
            return Response({"detail": "OFFER_NOT_FOUND"}, status=status.HTTP_404_NOT_FOUND)
        if not offer.applies_to_all and not OfferTarget.objects.filter(offer=offer, user=request.user).exists():
            return Response({"detail": "OFFER_NOT_AVAILABLE"}, status=status.HTTP_403_FORBIDDEN)
        OfferRedemption.objects.get_or_create(offer=offer, user=request.user, tenant=request.user.tenant)
        return Response({"detail": "OK"})


class ClientCouponsView(TenantMixin, APIView):
    permission_classes = [IsTenantMember, IsClient]

    def get(self, request, tenant_slug):
        assignments = CouponAssignment.objects.filter(card=request.user.card).order_by("-created_at")
        return Response(CouponAssignmentSerializer(assignments, many=True).data)


class ClientQRIssueView(TenantMixin, APIView):
    permission_classes = [IsTenantMember, IsClient]

    def post(self, request, tenant_slug):
        if not request.user.email_verified:
            return Response({"detail": "EMAIL_NOT_VERIFIED"}, status=status.HTTP_400_BAD_REQUEST)
        token = uuid4().hex
        expires_at = timezone.now() + timedelta(seconds=10)
        OneTimeQR.objects.create(card=request.user.card, tenant=request.tenant, token=token, expires_at=expires_at)
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
        qr, error = validate_qr(request.tenant, token)
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
            rule = get_rule(tenant, original.location, card.user)
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
        first_name = serializer.validated_data["first_name"]
        last_name = serializer.validated_data["last_name"]
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
            is_active=True,
            first_name=first_name,
            last_name=last_name,
        )
        StaffProfile.objects.create(user=user, tenant=tenant, location=location)
        return Response({"detail": "CREATED"}, status=status.HTTP_201_CREATED)

    def delete(self, request, tenant_slug, user_id=None):
        user_id = user_id or self.kwargs.get("user_id")
        if not user_id:
            return Response({"detail": "USER_ID_REQUIRED"}, status=status.HTTP_400_BAD_REQUEST)
        if int(user_id) == request.user.id:
            return Response({"detail": "CANNOT_DELETE_SELF"}, status=status.HTTP_400_BAD_REQUEST)
        user = User.objects.filter(
            tenant=request.user.tenant,
            id=user_id,
            role__in=[User.Role.ADMIN, User.Role.CASHIER],
        ).first()
        if not user:
            return Response({"detail": "USER_NOT_FOUND"}, status=status.HTTP_404_NOT_FOUND)
        user.delete()
        audit_log(request.user.tenant, request.user, "staff_delete", {"user_id": user_id})
        return Response({"detail": "DELETED"})


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

    def delete(self, request, tenant_slug, location_id=None):
        location_id = location_id or self.kwargs.get("location_id")
        if not location_id:
            return Response({"detail": "LOCATION_ID_REQUIRED"}, status=status.HTTP_400_BAD_REQUEST)
        location = Location.objects.filter(tenant=request.user.tenant, id=location_id).first()
        if not location:
            return Response({"detail": "LOCATION_NOT_FOUND"}, status=status.HTTP_404_NOT_FOUND)
        location.delete()
        audit_log(request.user.tenant, request.user, "location_delete", {"location_id": location_id})
        return Response({"detail": "DELETED"})


class AdminRulesView(TenantMixin, APIView):
    permission_classes = [IsTenantMember, IsAdmin]

    def get(self, request, tenant_slug):
        rules = LoyaltyRule.objects.filter(tenant=request.user.tenant).order_by("-id")
        return Response(LoyaltyRuleSerializer(rules, many=True).data)

    def post(self, request, tenant_slug):
        serializer = LoyaltyRuleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        client_ids = data.pop("client_ids", [])
        applies_to_all = data.get("applies_to_all", True)
        if client_ids:
            applies_to_all = False
        data["applies_to_all"] = applies_to_all
        location = data.get("location")
        if applies_to_all:
            rule = (
                LoyaltyRule.objects.filter(
                    tenant=request.user.tenant,
                    location=location,
                    applies_to_all=True,
                )
                .order_by("-id")
                .first()
            )
            if rule:
                for field, value in data.items():
                    setattr(rule, field, value)
                rule.save()
            else:
                rule = LoyaltyRule.objects.create(tenant=request.user.tenant, **data)
            LoyaltyRule.objects.filter(
                tenant=request.user.tenant,
                location=location,
                applies_to_all=True,
            ).exclude(id=rule.id).delete()
            RuleTarget.objects.filter(rule=rule).delete()
        else:
            if client_ids:
                existing_rules = LoyaltyRule.objects.filter(
                    tenant=request.user.tenant,
                    location=location,
                    applies_to_all=False,
                    targets__user_id__in=client_ids,
                ).distinct()
                RuleTarget.objects.filter(rule__in=existing_rules, user_id__in=client_ids).delete()
                for existing in existing_rules:
                    if not RuleTarget.objects.filter(rule=existing).exists():
                        existing.delete()
            rule = LoyaltyRule.objects.create(tenant=request.user.tenant, **data)
            clients = User.objects.filter(
                tenant=request.user.tenant,
                role=User.Role.CLIENT,
                id__in=client_ids,
            )
            targets = [
                RuleTarget(rule=rule, user=client, tenant=request.user.tenant)
                for client in clients
            ]
            RuleTarget.objects.bulk_create(targets, ignore_conflicts=True)
        return Response(LoyaltyRuleSerializer(rule).data)

    def delete(self, request, tenant_slug, rule_id=None):
        rule_id = rule_id or self.kwargs.get("rule_id")
        if not rule_id:
            return Response({"detail": "RULE_ID_REQUIRED"}, status=status.HTTP_400_BAD_REQUEST)
        rule = LoyaltyRule.objects.filter(tenant=request.user.tenant, id=rule_id).first()
        if not rule:
            return Response({"detail": "RULE_NOT_FOUND"}, status=status.HTTP_404_NOT_FOUND)
        rule.delete()
        audit_log(request.user.tenant, request.user, "rule_delete", {"rule_id": rule_id})
        return Response({"detail": "DELETED"})


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
        data = serializer.validated_data
        client_ids = data.pop("client_ids", [])
        applies_to_all = data.get("applies_to_all", True)
        if client_ids:
            applies_to_all = False
        data["applies_to_all"] = applies_to_all
        offer = Offer.objects.create(tenant=request.user.tenant, **data)
        if not applies_to_all and client_ids:
            clients = User.objects.filter(
                tenant=request.user.tenant,
                role=User.Role.CLIENT,
                id__in=client_ids,
            )
            targets = [
                OfferTarget(offer=offer, user=client, tenant=request.user.tenant)
                for client in clients
            ]
            OfferTarget.objects.bulk_create(targets, ignore_conflicts=True)
        return Response(OfferSerializer(offer).data, status=status.HTTP_201_CREATED)

    def delete(self, request, tenant_slug, offer_id=None):
        offer_id = offer_id or self.kwargs.get("offer_id")
        if not offer_id:
            return Response({"detail": "OFFER_ID_REQUIRED"}, status=status.HTTP_400_BAD_REQUEST)
        offer = Offer.objects.filter(tenant=request.user.tenant, id=offer_id).first()
        if not offer:
            return Response({"detail": "OFFER_NOT_FOUND"}, status=status.HTTP_404_NOT_FOUND)
        offer.delete()
        audit_log(request.user.tenant, request.user, "offer_delete", {"offer_id": offer_id})
        return Response({"detail": "DELETED"})


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
    tenant = getattr(request, "tenant", None) or Tenant.objects.get(slug=tenant_slug)
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
        qr = (
            OneTimeQR.objects.select_for_update()
            .select_related("card", "card__user")
            .filter(token=token, tenant=tenant)
            .first()
        )
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

        rule = get_rule(tenant, location, card.user)
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
