from django.core.management.base import BaseCommand
from django.utils.crypto import get_random_string
from django.utils import timezone
from loyalty.models import (
    Tenant,
    OrganizationSettings,
    Location,
    LoyaltyRule,
    User,
    StaffProfile,
    LoyaltyCard,
    Offer,
    Coupon,
    CouponAssignment,
)


class Command(BaseCommand):
    help = "Seed demo tenant and users"

    def handle(self, *args, **options):
        tenant, created = Tenant.objects.get_or_create(
            slug="demo",
            defaults={
                "name": "Demo Tenant",
                "pos_api_key": get_random_string(32),
            },
        )
        if not created and not tenant.pos_api_key:
            tenant.pos_api_key = get_random_string(32)
            tenant.save()

        OrganizationSettings.objects.get_or_create(
            tenant=tenant,
            defaults={
                "brand_color": "#2d6a4f",
                "email_from": "no-reply@demo.local",
            },
        )

        location, _ = Location.objects.get_or_create(tenant=tenant, name="Main")
        LoyaltyRule.objects.get_or_create(
            tenant=tenant,
            location=None,
            defaults={
                "earn_percent": 3,
                "min_amount": 0,
                "bronze_threshold": 0,
                "silver_threshold": 500,
                "gold_threshold": 1500,
            },
        )

        admin_user = User.objects.filter(tenant=tenant, email="admin@demo.local").first()
        if not admin_user:
            admin_user = User.objects.create_user(
                email="admin@demo.local",
                password="12345678",
                tenant=tenant,
                role=User.Role.ADMIN,
                email_verified=True,
                phone_verified=True,
            )
            StaffProfile.objects.create(user=admin_user, tenant=tenant, location=location)

        cashier = User.objects.filter(tenant=tenant, email="cashier@demo.local").first()
        if not cashier:
            cashier = User.objects.create_user(
                email="cashier@demo.local",
                password="12345678",
                tenant=tenant,
                role=User.Role.CASHIER,
                email_verified=True,
                phone_verified=True,
            )
            StaffProfile.objects.create(user=cashier, tenant=tenant, location=location)

        client = User.objects.filter(tenant=tenant, email="client@demo.local").first()
        if not client:
            client = User.objects.create_user(
                email="client@demo.local",
                password="12345678",
                tenant=tenant,
                role=User.Role.CLIENT,
                email_verified=True,
                phone_verified=True,
            )
            card = LoyaltyCard.objects.create(user=client, tenant=tenant, current_points=120)
        else:
            card = getattr(client, "card", None)

        offer, _ = Offer.objects.get_or_create(
            tenant=tenant,
            title="Welcome Bonus",
            defaults={
                "description": "Earn +50 points on your first purchase.",
                "type": Offer.Type.BONUS,
                "bonus_points": 50,
                "is_active": True,
                "active_from": timezone.now(),
            },
        )

        coupon, _ = Coupon.objects.get_or_create(
            tenant=tenant,
            code="WELCOME10",
            defaults={
                "title": "10% Off",
                "description": "Welcome coupon for new clients",
                "active_from": timezone.now(),
            },
        )
        if card:
            CouponAssignment.objects.get_or_create(card=card, coupon=coupon, tenant=tenant)

        self.stdout.write(self.style.SUCCESS("Seeded demo tenant (slug=demo)"))
        self.stdout.write(self.style.SUCCESS(f"POS API key: {tenant.pos_api_key}"))
        self.stdout.write(self.style.SUCCESS("Portals:"))
        self.stdout.write(self.style.SUCCESS("- Client: http://localhost:5173/t/demo/login"))
        self.stdout.write(self.style.SUCCESS("- Cashier: http://localhost:5173/t/demo/cashier/login"))
        self.stdout.write(self.style.SUCCESS("- Admin: http://localhost:5173/t/demo/admin/login"))
