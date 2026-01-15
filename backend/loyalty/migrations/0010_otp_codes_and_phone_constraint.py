from django.db import migrations, models
import django.db.models.deletion
import django.db.models.expressions


class Migration(migrations.Migration):
    dependencies = [
        ("loyalty", "0009_remove_loyaltyrule_unique"),
    ]

    operations = [
        migrations.CreateModel(
            name="OneTimeCode",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("purpose", models.CharField(choices=[("EMAIL_LOGIN", "Email login"), ("TELEGRAM_PHONE_LOGIN", "Telegram phone login")], max_length=32)),
                ("recipient", models.CharField(max_length=255)),
                ("code_hash", models.CharField(max_length=128)),
                ("chat_id", models.BigIntegerField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("expires_at", models.DateTimeField()),
                ("attempts", models.IntegerField(default=0)),
                ("consumed_at", models.DateTimeField(blank=True, null=True)),
                ("tenant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="otp_codes", to="loyalty.tenant", verbose_name="Tenant")),
            ],
            options={
                "verbose_name": "OTP code",
                "verbose_name_plural": "OTP codes",
            },
        ),
        migrations.AddIndex(
            model_name="onetimecode",
            index=models.Index(fields=["tenant", "purpose", "recipient"], name="loyalty_onet_tenant__1e5b6e_idx"),
        ),
        migrations.AddIndex(
            model_name="onetimecode",
            index=models.Index(fields=["tenant", "created_at"], name="loyalty_onet_tenant__0f12b4_idx"),
        ),
        migrations.AddIndex(
            model_name="onetimecode",
            index=models.Index(fields=["tenant", "chat_id"], name="loyalty_onet_tenant__1b6b0b_idx"),
        ),
        migrations.AddConstraint(
            model_name="user",
            constraint=models.UniqueConstraint(
                condition=django.db.models.expressions.Q(("phone", ""), _negated=True),
                fields=("tenant", "phone"),
                name="uniq_user_phone_per_tenant",
            ),
        ),
    ]
