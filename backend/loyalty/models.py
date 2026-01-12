from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils import timezone


def build_username(tenant, email: str) -> str:
    if tenant:
        return f"{tenant.id}:{email.lower()}"
    return email.lower()


class Tenant(models.Model):
    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=120)
    pos_api_key = models.CharField(max_length=64, blank=True)

    def __str__(self):
        return self.name


class OrganizationSettings(models.Model):
    tenant = models.OneToOneField(Tenant, on_delete=models.CASCADE, related_name="settings")
    brand_color = models.CharField(max_length=12, default="#2d6a4f")
    email_from = models.EmailField(blank=True)
    logo_url = models.URLField(blank=True)

    def __str__(self):
        return f"Settings:{self.tenant.slug}"


class Location(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="locations")
    name = models.CharField(max_length=120)
    address = models.CharField(max_length=255, blank=True)
    pos_api_key = models.CharField(max_length=64, blank=True)

    def __str__(self):
        return f"{self.tenant.slug}:{self.name}"


class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email)
        tenant = extra_fields.get("tenant")
        username = extra_fields.get("username") or build_username(tenant, email)
        user = self.model(email=email, username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        if not extra_fields.get("is_staff"):
            raise ValueError("Superuser must have is_staff=True.")
        if not extra_fields.get("is_superuser"):
            raise ValueError("Superuser must have is_superuser=True.")
        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    class Role(models.TextChoices):
        CLIENT = "CLIENT", "Client"
        CASHIER = "CASHIER", "Cashier"
        ADMIN = "ADMIN", "Admin"

    email = models.EmailField()
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="users", null=True, blank=True)
    phone = models.CharField(max_length=32, blank=True)
    phone_verified = models.BooleanField(default=False)
    email_verified = models.BooleanField(default=False)
    role = models.CharField(max_length=16, choices=Role.choices, default=Role.CLIENT)
    otp_hash = models.CharField(max_length=128, blank=True)
    otp_expires_at = models.DateTimeField(null=True, blank=True)
    otp_requested_at = models.DateTimeField(null=True, blank=True)
    otp_attempts = models.IntegerField(default=0)

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = []

    objects = UserManager()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["tenant", "email"], name="uniq_user_email_per_tenant"),
        ]

    def otp_is_valid(self, code_hash: str) -> bool:
        if not self.otp_hash or not self.otp_expires_at:
            return False
        if timezone.now() > self.otp_expires_at:
            return False
        return self.otp_hash == code_hash


class StaffProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="staff_profile")
    location = models.ForeignKey(Location, on_delete=models.SET_NULL, null=True, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"Staff:{self.user.email}"


class LoyaltyCard(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        BLOCKED = "BLOCKED", "Blocked"

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="card")
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="cards")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.ACTIVE)
    current_points = models.IntegerField(default=0)
    tier = models.CharField(max_length=16, default="Bronze")

    def __str__(self):
        return f"{self.tenant.slug}:{self.user.email}"


class OneTimeQR(models.Model):
    card = models.ForeignKey(LoyaltyCard, on_delete=models.CASCADE, related_name="qr_tokens")
    token = models.CharField(max_length=64, unique=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class LoyaltyRule(models.Model):
    class Rounding(models.TextChoices):
        FLOOR = "FLOOR", "Floor"
        ROUND = "ROUND", "Round"
        CEIL = "CEIL", "Ceil"

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="rules")
    location = models.ForeignKey(Location, on_delete=models.CASCADE, related_name="rules", null=True, blank=True)
    earn_percent = models.DecimalField(max_digits=5, decimal_places=2, default=3)
    rounding_mode = models.CharField(max_length=8, choices=Rounding.choices, default=Rounding.FLOOR)
    min_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    bronze_threshold = models.IntegerField(default=0)
    silver_threshold = models.IntegerField(default=500)
    gold_threshold = models.IntegerField(default=1500)

    class Meta:
        unique_together = ("tenant", "location")


class Offer(models.Model):
    class Type(models.TextChoices):
        MULTIPLIER = "MULTIPLIER", "Multiplier"
        BONUS = "BONUS", "Bonus"
        COUPON = "COUPON", "Coupon"

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="offers")
    title = models.CharField(max_length=160)
    description = models.TextField(blank=True)
    type = models.CharField(max_length=16, choices=Type.choices, default=Type.BONUS)
    multiplier = models.DecimalField(max_digits=6, decimal_places=2, default=1)
    bonus_points = models.IntegerField(default=0)
    active_from = models.DateTimeField(null=True, blank=True)
    active_to = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)


class Coupon(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="coupons")
    code = models.CharField(max_length=32)
    title = models.CharField(max_length=160)
    description = models.TextField(blank=True)
    active_from = models.DateTimeField(null=True, blank=True)
    active_to = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["tenant", "code"], name="uniq_coupon_code_per_tenant"),
        ]


class CouponAssignment(models.Model):
    class Status(models.TextChoices):
        UNUSED = "UNUSED", "Unused"
        USED = "USED", "Used"

    card = models.ForeignKey(LoyaltyCard, on_delete=models.CASCADE, related_name="coupon_assignments")
    coupon = models.ForeignKey(Coupon, on_delete=models.CASCADE, related_name="assignments")
    status = models.CharField(max_length=8, choices=Status.choices, default=Status.UNUSED)
    used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class LoyaltyOperation(models.Model):
    class Type(models.TextChoices):
        EARN = "EARN", "Earn"
        REDEEM = "REDEEM", "Redeem"
        REFUND = "REFUND", "Refund"

    class Source(models.TextChoices):
        POS = "POS", "POS"
        CASHIER_APP = "CASHIER_APP", "CashierApp"
        ADMIN_PORTAL = "ADMIN_PORTAL", "AdminPortal"

    class Status(models.TextChoices):
        SUCCESS = "SUCCESS", "Success"
        FAILED = "FAILED", "Failed"

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="operations")
    card = models.ForeignKey(LoyaltyCard, on_delete=models.CASCADE, related_name="operations")
    type = models.CharField(max_length=8, choices=Type.choices)
    source = models.CharField(max_length=16, choices=Source.choices)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    points = models.IntegerField(default=0)
    receipt_id = models.CharField(max_length=64, null=True, blank=True)
    order_id = models.CharField(max_length=64, null=True, blank=True)
    idempotency_key = models.CharField(max_length=64, unique=True, null=True, blank=True)
    original_operation = models.ForeignKey("self", on_delete=models.SET_NULL, null=True, blank=True)
    staff = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="staff_operations")
    location = models.ForeignKey(Location, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.SUCCESS)
    fail_reason = models.CharField(max_length=255, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["tenant", "receipt_id"]),
            models.Index(fields=["tenant", "idempotency_key"]),
            models.Index(fields=["card", "created_at"]),
        ]


class EmailVerificationCode(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="email_codes")
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    attempts = models.IntegerField(default=0)
    is_used = models.BooleanField(default=False)
    last_sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "is_used"]),
        ]


class AuditLog(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="audit_logs")
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=64)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
