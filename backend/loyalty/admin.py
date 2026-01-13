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

admin.site.site_header = "Панель администратора"
admin.site.site_title = "Администрирование"
admin.site.index_title = "Управление"

admin.site.register(Tenant)
admin.site.register(OrganizationSettings)
admin.site.register(Location)
admin.site.register(User)
admin.site.register(StaffProfile)
admin.site.register(LoyaltyCard)
admin.site.register(OneTimeQR)
admin.site.register(LoyaltyRule)
admin.site.register(Offer)
admin.site.register(Coupon)
admin.site.register(CouponAssignment)
admin.site.register(LoyaltyOperation)
admin.site.register(EmailVerificationCode)
admin.site.register(AuditLog)
