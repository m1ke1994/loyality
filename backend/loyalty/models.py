from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils import timezone


def build_username(tenant, email: str) -> str:
    if tenant:
        return f"{tenant.id}:{email.lower()}"
    return email.lower()


class Tenant(models.Model):
    slug = models.SlugField("Слаг", unique=True)
    name = models.CharField("Название", max_length=120)
    pos_api_key = models.CharField("POS API ключ", max_length=64, blank=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Арендатор"
        verbose_name_plural = "Арендаторы"


class OrganizationSettings(models.Model):
    tenant = models.OneToOneField(Tenant, on_delete=models.CASCADE, related_name="settings", verbose_name="Арендатор")
    brand_color = models.CharField("Цвет бренда", max_length=12, default="#2d6a4f")
    email_from = models.EmailField("Email отправителя", blank=True)
    logo_url = models.URLField("URL логотипа", blank=True)

    def __str__(self):
        return f"Settings:{self.tenant.slug}"

    class Meta:
        verbose_name = "Настройки организации"
        verbose_name_plural = "Настройки организации"


class Location(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="locations", verbose_name="Арендатор")
    name = models.CharField("Название", max_length=120)
    address = models.CharField("Адрес", max_length=255, blank=True)
    pos_api_key = models.CharField("POS API ключ", max_length=64, blank=True)

    def __str__(self):
        return f"{self.tenant.slug}:{self.name}"

    class Meta:
        verbose_name = "Локация"
        verbose_name_plural = "Локации"


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
        CLIENT = "CLIENT", "Клиент"
        CASHIER = "CASHIER", "Кассир"
        ADMIN = "ADMIN", "Администратор"

    email = models.EmailField("Email")
    tenant = models.ForeignKey(
        Tenant, on_delete=models.CASCADE, related_name="users", null=True, blank=True, verbose_name="Арендатор"
    )
    phone = models.CharField("Телефон", max_length=32, blank=True)
    phone_verified = models.BooleanField("Телефон подтверждён", default=False)
    email_verified = models.BooleanField("Email подтверждён", default=False)
    role = models.CharField("Роль", max_length=16, choices=Role.choices, default=Role.CLIENT)
    otp_hash = models.CharField("OTP хеш", max_length=128, blank=True)
    otp_expires_at = models.DateTimeField("OTP истекает", null=True, blank=True)
    otp_requested_at = models.DateTimeField("OTP запрошен", null=True, blank=True)
    otp_attempts = models.IntegerField("Попытки OTP", default=0)

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = []

    objects = UserManager()

    class Meta:
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"
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
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="staff_profile", verbose_name="Сотрудник")
    tenant = models.ForeignKey(
        Tenant, on_delete=models.CASCADE, related_name="staff_profiles", verbose_name="Tenant"
    )
    location = models.ForeignKey(
        Location, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Локация"
    )
    is_active = models.BooleanField("Активен", default=True)

    def __str__(self):
        return f"Staff:{self.tenant.slug}:{self.user.email}"

    class Meta:
        verbose_name = "Профиль сотрудника"
        verbose_name_plural = "Профили сотрудников"


class LoyaltyCard(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Активна"
        BLOCKED = "BLOCKED", "Заблокирована"

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="card", verbose_name="Клиент")
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="cards", verbose_name="Арендатор")
    status = models.CharField("Статус", max_length=16, choices=Status.choices, default=Status.ACTIVE)
    current_points = models.IntegerField("Текущие баллы", default=0)
    tier = models.CharField("Уровень", max_length=16, default="Bronze")

    def __str__(self):
        return f"{self.tenant.slug}:{self.user.email}"

    class Meta:
        verbose_name = "Карта лояльности"
        verbose_name_plural = "Карты лояльности"


class OneTimeQR(models.Model):
    card = models.ForeignKey(LoyaltyCard, on_delete=models.CASCADE, related_name="qr_tokens", verbose_name="Карта")
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="qr_tokens", verbose_name="Tenant")
    token = models.CharField("Токен", max_length=64, unique=True)
    expires_at = models.DateTimeField("Истекает")
    used_at = models.DateTimeField("Использован", null=True, blank=True)
    created_at = models.DateTimeField("Создан", auto_now_add=True)

    class Meta:
        verbose_name = "Одноразовый QR-код"
        verbose_name_plural = "Одноразовые QR-коды"
        indexes = [
            models.Index(fields=["tenant", "token"]),
            models.Index(fields=["tenant", "created_at"]),
        ]


class LoyaltyRule(models.Model):
    class Rounding(models.TextChoices):
        FLOOR = "FLOOR", "Вниз"
        ROUND = "ROUND", "Округлить"
        CEIL = "CEIL", "Вверх"

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="rules", verbose_name="Арендатор")
    location = models.ForeignKey(
        Location, on_delete=models.CASCADE, related_name="rules", null=True, blank=True, verbose_name="Локация"
    )
    earn_percent = models.DecimalField("Процент начисления", max_digits=5, decimal_places=2, default=3)
    rounding_mode = models.CharField("Режим округления", max_length=8, choices=Rounding.choices, default=Rounding.FLOOR)
    min_amount = models.DecimalField("Минимальная сумма", max_digits=12, decimal_places=2, default=0)
    bronze_threshold = models.IntegerField("Порог Bronze", default=0)
    silver_threshold = models.IntegerField("Порог Silver", default=500)
    gold_threshold = models.IntegerField("Порог Gold", default=1500)

    class Meta:
        verbose_name = "Правило лояльности"
        verbose_name_plural = "Правила лояльности"
        unique_together = ("tenant", "location")


class Offer(models.Model):
    class Type(models.TextChoices):
        MULTIPLIER = "MULTIPLIER", "Множитель"
        BONUS = "BONUS", "Бонус"
        COUPON = "COUPON", "Купон"

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="offers", verbose_name="Арендатор")
    title = models.CharField("Название", max_length=160)
    description = models.TextField("Описание", blank=True)
    type = models.CharField("Тип", max_length=16, choices=Type.choices, default=Type.BONUS)
    multiplier = models.DecimalField("Множитель", max_digits=6, decimal_places=2, default=1)
    bonus_points = models.IntegerField("Бонусные баллы", default=0)
    active_from = models.DateTimeField("Активно с", null=True, blank=True)
    active_to = models.DateTimeField("Активно по", null=True, blank=True)
    is_active = models.BooleanField("Активно", default=True)
    applies_to_all = models.BooleanField("Applies to all clients", default=True)

    class Meta:
        verbose_name = "Предложение"
        verbose_name_plural = "Предложения"


class OfferTarget(models.Model):
    offer = models.ForeignKey(Offer, on_delete=models.CASCADE, related_name="targets")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="offer_targets")
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="offer_targets")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Offer target"
        verbose_name_plural = "Offer targets"
        constraints = [
            models.UniqueConstraint(fields=["offer", "user"], name="uniq_offer_target"),
        ]
        indexes = [
            models.Index(fields=["tenant", "user"]),
            models.Index(fields=["tenant", "offer"]),
        ]


class Coupon(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="coupons", verbose_name="Арендатор")
    code = models.CharField("Код", max_length=32)
    title = models.CharField("Название", max_length=160)
    description = models.TextField("Описание", blank=True)
    active_from = models.DateTimeField("Активно с", null=True, blank=True)
    active_to = models.DateTimeField("Активно по", null=True, blank=True)

    class Meta:
        verbose_name = "Купон"
        verbose_name_plural = "Купоны"
        constraints = [
            models.UniqueConstraint(fields=["tenant", "code"], name="uniq_coupon_code_per_tenant"),
        ]


class CouponAssignment(models.Model):
    class Status(models.TextChoices):
        UNUSED = "UNUSED", "Не использован"
        USED = "USED", "Использован"

    card = models.ForeignKey(LoyaltyCard, on_delete=models.CASCADE, related_name="coupon_assignments", verbose_name="Карта")
    coupon = models.ForeignKey(Coupon, on_delete=models.CASCADE, related_name="assignments", verbose_name="Купон")
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="coupon_assignments", verbose_name="Tenant")
    status = models.CharField("Статус", max_length=8, choices=Status.choices, default=Status.UNUSED)
    used_at = models.DateTimeField("Использован", null=True, blank=True)
    created_at = models.DateTimeField("Создан", auto_now_add=True)

    class Meta:
        verbose_name = "Выданный купон"
        verbose_name_plural = "Выданные купоны"
        indexes = [
            models.Index(fields=["tenant", "created_at"]),
            models.Index(fields=["tenant", "status"]),
        ]


class LoyaltyOperation(models.Model):
    class Type(models.TextChoices):
        EARN = "EARN", "Начисление"
        REDEEM = "REDEEM", "Списание"
        REFUND = "REFUND", "Возврат"

    class Source(models.TextChoices):
        POS = "POS", "POS"
        CASHIER_APP = "CASHIER_APP", "Касса"
        ADMIN_PORTAL = "ADMIN_PORTAL", "Админ-портал"

    class Status(models.TextChoices):
        SUCCESS = "SUCCESS", "Успешно"
        FAILED = "FAILED", "Ошибка"

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="operations", verbose_name="Арендатор")
    card = models.ForeignKey(LoyaltyCard, on_delete=models.CASCADE, related_name="operations", verbose_name="Карта")
    type = models.CharField("Тип", max_length=8, choices=Type.choices)
    source = models.CharField("Источник", max_length=16, choices=Source.choices)
    amount = models.DecimalField("Сумма", max_digits=12, decimal_places=2)
    points = models.IntegerField("Баллы", default=0)
    receipt_id = models.CharField("Чек", max_length=64, null=True, blank=True)
    order_id = models.CharField("Заказ", max_length=64, null=True, blank=True)
    idempotency_key = models.CharField("Ключ идемпотентности", max_length=64, unique=True, null=True, blank=True)
    original_operation = models.ForeignKey("self", on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Операция-источник")
    staff = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="staff_operations", verbose_name="Сотрудник"
    )
    location = models.ForeignKey(Location, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Локация")
    status = models.CharField("Статус", max_length=16, choices=Status.choices, default=Status.SUCCESS)
    fail_reason = models.CharField("Причина ошибки", max_length=255, blank=True)
    metadata = models.JSONField("Метаданные", default=dict, blank=True)
    created_at = models.DateTimeField("Создан", auto_now_add=True)

    class Meta:
        verbose_name = "Операция лояльности"
        verbose_name_plural = "Операции лояльности"
        indexes = [
            models.Index(fields=["tenant", "receipt_id"]),
            models.Index(fields=["tenant", "idempotency_key"]),
            models.Index(fields=["card", "created_at"]),
        ]


class EmailVerificationCode(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="email_codes", verbose_name="Пользователь")
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="email_codes", verbose_name="Tenant")
    code = models.CharField("Код", max_length=6)
    created_at = models.DateTimeField("Создан", auto_now_add=True)
    expires_at = models.DateTimeField("Истекает")
    attempts = models.IntegerField("Попытки", default=0)
    is_used = models.BooleanField("Использован", default=False)
    last_sent_at = models.DateTimeField("Последняя отправка", null=True, blank=True)

    class Meta:
        verbose_name = "Код подтверждения email"
        verbose_name_plural = "Коды подтверждения email"
        indexes = [
            models.Index(fields=["tenant", "user", "is_used"]),
            models.Index(fields=["tenant", "created_at"]),
        ]
class AuditLog(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="audit_logs", verbose_name="Арендатор")
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Пользователь")
    action = models.CharField("Действие", max_length=64)
    metadata = models.JSONField("Метаданные", default=dict, blank=True)
    created_at = models.DateTimeField("Создан", auto_now_add=True)

    class Meta:
        verbose_name = "Журнал аудита"
        verbose_name_plural = "Журналы аудита"
