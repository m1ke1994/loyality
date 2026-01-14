from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
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
    Coupon,
    CouponAssignment,
    LoyaltyOperation,
    EmailVerificationCode,
    AuditLog,
)

admin.site.site_header = "Loyalty Admin"
admin.site.site_title = "Loyalty Admin"
admin.site.index_title = "Admin"


class TenantScopedAdmin(admin.ModelAdmin):
    tenant_field = "tenant"

    def get_tenant(self, request):
        if request.user.is_superuser:
            return None
        return getattr(request.user, "tenant", None)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        tenant = self.get_tenant(request)
        if tenant:
            return qs.filter(**{self.tenant_field: tenant})
        return qs.none()

    def save_model(self, request, obj, form, change):
        tenant = self.get_tenant(request)
        if tenant and hasattr(obj, self.tenant_field):
            setattr(obj, self.tenant_field, tenant)
        super().save_model(request, obj, form, change)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        tenant = self.get_tenant(request)
        if tenant:
            if db_field.name == self.tenant_field:
                kwargs["queryset"] = Tenant.objects.filter(id=tenant.id)
            elif db_field.name == "user":
                kwargs["queryset"] = User.objects.filter(tenant=tenant)
            elif db_field.name == "card":
                kwargs["queryset"] = LoyaltyCard.objects.filter(tenant=tenant)
            elif db_field.name == "coupon":
                kwargs["queryset"] = Coupon.objects.filter(tenant=tenant)
            elif db_field.name == "location":
                kwargs["queryset"] = Location.objects.filter(tenant=tenant)
            elif db_field.name == "staff":
                kwargs["queryset"] = User.objects.filter(tenant=tenant)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


class OrganizationSettingsInline(admin.StackedInline):
    model = OrganizationSettings
    can_delete = False
    extra = 0


class LocationInline(admin.TabularInline):
    model = Location
    extra = 0


class TenantAdmin(admin.ModelAdmin):
    list_display = ("id", "slug", "name", "pos_api_key")
    search_fields = ("slug", "name")
    inlines = [OrganizationSettingsInline, LocationInline]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        tenant = getattr(request.user, "tenant", None)
        if tenant:
            return qs.filter(id=tenant.id)
        return qs.none()

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


class UserAdmin(DjangoUserAdmin, TenantScopedAdmin):
    list_display = ("id", "email", "username", "role", "tenant", "email_verified", "is_active", "is_staff", "is_superuser")
    list_filter = ("role", "email_verified", "is_active", "is_staff", "is_superuser", "tenant")
    search_fields = ("email", "username", "phone")
    ordering = ("id",)
    fieldsets = (
        (None, {"fields": ("username", "password")}),
        ("Personal info", {"fields": ("email", "phone", "email_verified", "phone_verified")}),
        ("Tenant", {"fields": ("tenant", "role")}),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "username", "password1", "password2", "tenant", "role", "email_verified", "is_active"),
            },
        ),
    )

    def get_readonly_fields(self, request, obj=None):
        readonly = list(super().get_readonly_fields(request, obj))
        if not request.user.is_superuser:
            readonly += ["tenant", "is_superuser", "is_staff", "groups", "user_permissions"]
        return readonly

    def save_model(self, request, obj, form, change):
        tenant = self.get_tenant(request)
        if tenant:
            obj.tenant = tenant
        super().save_model(request, obj, form, change)


class StaffProfileAdmin(TenantScopedAdmin):
    list_display = ("id", "user", "tenant", "location", "is_active")
    list_filter = ("tenant", "is_active")
    search_fields = ("user__email", "user__username")
    raw_id_fields = ("user", "tenant", "location")

    def save_model(self, request, obj, form, change):
        if not request.user.is_superuser and obj.user and obj.user.tenant:
            obj.tenant = obj.user.tenant
        super().save_model(request, obj, form, change)


class LocationAdmin(TenantScopedAdmin):
    list_display = ("id", "name", "tenant", "pos_api_key")
    search_fields = ("name",)
    list_filter = ("tenant",)


class LoyaltyCardAdmin(TenantScopedAdmin):
    list_display = ("id", "user", "tenant", "status", "current_points", "tier")
    list_filter = ("tenant", "status", "tier")
    search_fields = ("user__email",)


class OneTimeQRAdmin(TenantScopedAdmin):
    list_display = ("id", "token", "tenant", "card", "expires_at", "used_at", "created_at")
    list_filter = ("tenant", "used_at")
    search_fields = ("token", "card__user__email")


class LoyaltyRuleAdmin(TenantScopedAdmin):
    list_display = ("id", "tenant", "location", "earn_percent", "rounding_mode", "min_amount")
    list_filter = ("tenant", "rounding_mode")


class OfferAdmin(TenantScopedAdmin):
    list_display = ("id", "tenant", "title", "type", "is_active", "active_from", "active_to")
    list_filter = ("tenant", "type", "is_active")
    search_fields = ("title",)


class CouponAdmin(TenantScopedAdmin):
    list_display = ("id", "tenant", "code", "title", "active_from", "active_to")
    list_filter = ("tenant",)
    search_fields = ("code", "title")


class CouponAssignmentAdmin(TenantScopedAdmin):
    list_display = ("id", "tenant", "coupon", "card", "status", "used_at", "created_at")
    list_filter = ("tenant", "status")
    search_fields = ("coupon__code", "card__user__email")


class LoyaltyOperationAdmin(TenantScopedAdmin):
    list_display = (
        "id",
        "tenant",
        "type",
        "source",
        "status",
        "card",
        "points",
        "amount",
        "receipt_id",
        "created_at",
    )
    list_filter = ("tenant", "type", "source", "status")
    search_fields = ("receipt_id", "order_id", "idempotency_key", "card__user__email")
    date_hierarchy = "created_at"


class OrganizationSettingsAdmin(TenantScopedAdmin):
    list_display = ("id", "tenant", "brand_color", "email_from")
    list_filter = ("tenant",)


class EmailVerificationCodeAdmin(TenantScopedAdmin):
    list_display = ("id", "tenant", "user", "code", "is_used", "created_at", "expires_at")
    list_filter = ("tenant", "is_used")
    search_fields = ("user__email", "code")


class AuditLogAdmin(TenantScopedAdmin):
    list_display = ("id", "tenant", "user", "action", "created_at")
    list_filter = ("tenant", "action")
    search_fields = ("action", "user__email")
    date_hierarchy = "created_at"


admin.site.register(Tenant, TenantAdmin)
admin.site.register(OrganizationSettings, OrganizationSettingsAdmin)
admin.site.register(Location, LocationAdmin)
admin.site.register(User, UserAdmin)
admin.site.register(StaffProfile, StaffProfileAdmin)
admin.site.register(LoyaltyCard, LoyaltyCardAdmin)
admin.site.register(OneTimeQR, OneTimeQRAdmin)
admin.site.register(LoyaltyRule, LoyaltyRuleAdmin)
admin.site.register(Offer, OfferAdmin)
admin.site.register(Coupon, CouponAdmin)
admin.site.register(CouponAssignment, CouponAssignmentAdmin)
admin.site.register(LoyaltyOperation, LoyaltyOperationAdmin)
admin.site.register(EmailVerificationCode, EmailVerificationCodeAdmin)
admin.site.register(AuditLog, AuditLogAdmin)
