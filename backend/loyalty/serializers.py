from rest_framework import serializers
from .models import (
    User,
    LoyaltyOperation,
    Offer,
    OfferTarget,
    CouponAssignment,
    Location,
    LoyaltyRule,
    OrganizationSettings,
)


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(min_length=8)
    password2 = serializers.CharField(min_length=8)

    def validate(self, attrs):
        if attrs.get("password") != attrs.get("password2"):
            raise serializers.ValidationError({"password2": "Passwords do not match"})
        return attrs


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()


class EmailRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class EmailConfirmSerializer(serializers.Serializer):
    email = serializers.EmailField()
    code = serializers.RegexField(regex=r"^\d{6}$")


class PhoneRequestSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=32)


class PhoneConfirmSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=6)


class QRValidateSerializer(serializers.Serializer):
    qr_payload = serializers.CharField()


class PointsSerializer(serializers.Serializer):
    qr_payload = serializers.CharField()
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    idempotency_key = serializers.CharField(max_length=64)
    location_id = serializers.IntegerField(required=False)
    receipt_id = serializers.CharField(max_length=64, required=False)


class RefundSerializer(serializers.Serializer):
    receipt_id = serializers.CharField(max_length=64)
    idempotency_key = serializers.CharField(max_length=64)


class POSPointsSerializer(serializers.Serializer):
    qr_payload = serializers.CharField()
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    receipt_id = serializers.CharField(max_length=64)
    location_id = serializers.IntegerField(required=True)


class PasswordChangeSerializer(serializers.Serializer):
    current_password = serializers.CharField()
    new_password = serializers.CharField(min_length=8)


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "email", "phone", "phone_verified", "email_verified", "role")


class OperationSerializer(serializers.ModelSerializer):
    class Meta:
        model = LoyaltyOperation
        fields = (
            "id",
            "type",
            "source",
            "amount",
            "points",
            "receipt_id",
            "order_id",
            "status",
            "fail_reason",
            "metadata",
            "created_at",
        )


class OfferSerializer(serializers.ModelSerializer):
    client_ids = serializers.ListField(child=serializers.IntegerField(), write_only=True, required=False)
    target_ids = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Offer
        fields = (
            "id",
            "title",
            "description",
            "type",
            "multiplier",
            "bonus_points",
            "active_from",
            "active_to",
            "is_active",
            "applies_to_all",
            "target_ids",
            "client_ids",
        )

    def get_target_ids(self, obj):
        return list(OfferTarget.objects.filter(offer=obj).values_list("user_id", flat=True))


class CouponAssignmentSerializer(serializers.ModelSerializer):
    coupon_title = serializers.CharField(source="coupon.title", read_only=True)
    coupon_code = serializers.CharField(source="coupon.code", read_only=True)
    coupon_description = serializers.CharField(source="coupon.description", read_only=True)

    class Meta:
        model = CouponAssignment
        fields = ("id", "coupon_title", "coupon_code", "coupon_description", "status", "used_at", "created_at")


class LocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Location
        fields = ("id", "name", "address")


class LoyaltyRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = LoyaltyRule
        fields = (
            "id",
            "location",
            "earn_percent",
            "rounding_mode",
            "min_amount",
            "bronze_threshold",
            "silver_threshold",
            "gold_threshold",
        )


class OrganizationSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrganizationSettings
        fields = ("brand_color", "email_from", "logo_url")


class StaffCreateSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(min_length=8)
    role = serializers.ChoiceField(choices=["CASHIER", "ADMIN"])
    location_id = serializers.IntegerField(required=False)
