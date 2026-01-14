from django.contrib import admin
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


class StaffProfileAdmin(TenantScopedAdmin):
    def save_model(self, request, obj, form, change):
        if not request.user.is_superuser and obj.user and obj.user.tenant:
            obj.tenant = obj.user.tenant
        super().save_model(request, obj, form, change)


class UserAdmin(TenantScopedAdmin):
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


admin.site.register(Tenant, TenantScopedAdmin)
admin.site.register(OrganizationSettings, TenantScopedAdmin)
admin.site.register(Location, TenantScopedAdmin)
admin.site.register(User, UserAdmin)
admin.site.register(StaffProfile, StaffProfileAdmin)
admin.site.register(LoyaltyCard, TenantScopedAdmin)
admin.site.register(OneTimeQR, TenantScopedAdmin)
admin.site.register(LoyaltyRule, TenantScopedAdmin)
admin.site.register(Offer, TenantScopedAdmin)
admin.site.register(Coupon, TenantScopedAdmin)
admin.site.register(CouponAssignment, TenantScopedAdmin)
admin.site.register(LoyaltyOperation, TenantScopedAdmin)
admin.site.register(EmailVerificationCode, TenantScopedAdmin)
admin.site.register(AuditLog, TenantScopedAdmin)
