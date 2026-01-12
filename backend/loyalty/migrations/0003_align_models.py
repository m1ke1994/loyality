from django.db import migrations, models
import django.db.models.deletion


def populate_usernames(apps, schema_editor):
    User = apps.get_model("loyalty", "User")
    for user in User.objects.filter(username__isnull=True):
        email = (user.email or "").lower()
        if user.tenant_id:
            user.username = f"{user.tenant_id}:{email}"
        else:
            user.username = email
        user.save(update_fields=["username"])


class Migration(migrations.Migration):
    dependencies = [
        ("loyalty", "0002_create_email_verification_code"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="username",
            field=models.CharField(blank=True, max_length=150, null=True, unique=True),
        ),
        migrations.RunPython(populate_usernames, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="user",
            name="username",
            field=models.CharField(max_length=150, unique=True),
        ),
        migrations.AlterField(
            model_name="user",
            name="email",
            field=models.EmailField(max_length=254),
        ),
        migrations.AddField(
            model_name="user",
            name="email_verified",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="user",
            name="otp_attempts",
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name="user",
            name="otp_hash",
            field=models.CharField(blank=True, max_length=128),
        ),
        migrations.AddField(
            model_name="user",
            name="otp_requested_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.RemoveField(
            model_name="user",
            name="otp_code",
        ),
        migrations.AddField(
            model_name="location",
            name="address",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name="loyaltycard",
            name="tier",
            field=models.CharField(default="Bronze", max_length=16),
        ),
        migrations.AddField(
            model_name="loyaltyrule",
            name="rounding_mode",
            field=models.CharField(choices=[("FLOOR", "Floor"), ("ROUND", "Round"), ("CEIL", "Ceil")], default="FLOOR", max_length=8),
        ),
        migrations.AddField(
            model_name="loyaltyrule",
            name="min_amount",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
        migrations.AddField(
            model_name="loyaltyrule",
            name="bronze_threshold",
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name="loyaltyrule",
            name="silver_threshold",
            field=models.IntegerField(default=500),
        ),
        migrations.AddField(
            model_name="loyaltyrule",
            name="gold_threshold",
            field=models.IntegerField(default=1500),
        ),
        migrations.AddField(
            model_name="loyaltyoperation",
            name="order_id",
            field=models.CharField(blank=True, max_length=64, null=True),
        ),
        migrations.AddField(
            model_name="loyaltyoperation",
            name="original_operation",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to="loyalty.loyaltyoperation"),
        ),
        migrations.AddField(
            model_name="loyaltyoperation",
            name="metadata",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.CreateModel(
            name="OrganizationSettings",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("brand_color", models.CharField(default="#2d6a4f", max_length=12)),
                ("email_from", models.EmailField(blank=True, max_length=254)),
                ("logo_url", models.URLField(blank=True)),
                (
                    "tenant",
                    models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="settings", to="loyalty.tenant"),
                ),
            ],
        ),
        migrations.CreateModel(
            name="StaffProfile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("is_active", models.BooleanField(default=True)),
                (
                    "location",
                    models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to="loyalty.location"),
                ),
                (
                    "user",
                    models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="staff_profile", to="loyalty.user"),
                ),
            ],
        ),
        migrations.CreateModel(
            name="Offer",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=160)),
                ("description", models.TextField(blank=True)),
                (
                    "type",
                    models.CharField(
                        choices=[("MULTIPLIER", "Multiplier"), ("BONUS", "Bonus"), ("COUPON", "Coupon")],
                        default="BONUS",
                        max_length=16,
                    ),
                ),
                ("multiplier", models.DecimalField(decimal_places=2, default=1, max_digits=6)),
                ("bonus_points", models.IntegerField(default=0)),
                ("active_from", models.DateTimeField(blank=True, null=True)),
                ("active_to", models.DateTimeField(blank=True, null=True)),
                ("is_active", models.BooleanField(default=True)),
                (
                    "tenant",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="offers", to="loyalty.tenant"),
                ),
            ],
        ),
        migrations.CreateModel(
            name="Coupon",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.CharField(max_length=32)),
                ("title", models.CharField(max_length=160)),
                ("description", models.TextField(blank=True)),
                ("active_from", models.DateTimeField(blank=True, null=True)),
                ("active_to", models.DateTimeField(blank=True, null=True)),
                (
                    "tenant",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="coupons", to="loyalty.tenant"),
                ),
            ],
        ),
        migrations.CreateModel(
            name="CouponAssignment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("status", models.CharField(choices=[("UNUSED", "Unused"), ("USED", "Used")], default="UNUSED", max_length=8)),
                ("used_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "card",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="coupon_assignments", to="loyalty.loyaltycard"),
                ),
                (
                    "coupon",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="assignments", to="loyalty.coupon"),
                ),
            ],
        ),
        migrations.CreateModel(
            name="AuditLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("action", models.CharField(max_length=64)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "tenant",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="audit_logs", to="loyalty.tenant"),
                ),
                (
                    "user",
                    models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to="loyalty.user"),
                ),
            ],
        ),
        migrations.AddConstraint(
            model_name="coupon",
            constraint=models.UniqueConstraint(fields=("tenant", "code"), name="uniq_coupon_code_per_tenant"),
        ),
    ]
