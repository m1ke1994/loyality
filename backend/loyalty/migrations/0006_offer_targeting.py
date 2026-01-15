from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("loyalty", "0005_tenant_isolation"),
    ]

    operations = [
        migrations.AddField(
            model_name="offer",
            name="applies_to_all",
            field=models.BooleanField(default=True, verbose_name="Applies to all clients"),
        ),
        migrations.CreateModel(
            name="OfferTarget",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("offer", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="targets", to="loyalty.offer")),
                ("tenant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="offer_targets", to="loyalty.tenant")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="offer_targets", to="loyalty.user")),
            ],
            options={
                "verbose_name": "Offer target",
                "verbose_name_plural": "Offer targets",
            },
        ),
        migrations.AddConstraint(
            model_name="offertarget",
            constraint=models.UniqueConstraint(fields=("offer", "user"), name="uniq_offer_target"),
        ),
        migrations.AddIndex(
            model_name="offertarget",
            index=models.Index(fields=["tenant", "user"], name="loyalty_offe_tenant__ae2c63_idx"),
        ),
        migrations.AddIndex(
            model_name="offertarget",
            index=models.Index(fields=["tenant", "offer"], name="loyalty_offe_tenant__b2d05f_idx"),
        ),
    ]
