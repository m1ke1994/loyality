from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("loyalty", "0006_offer_targeting"),
    ]

    operations = [
        migrations.CreateModel(
            name="OfferRedemption",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("used_at", models.DateTimeField(auto_now_add=True)),
                ("offer", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="redemptions", to="loyalty.offer")),
                ("tenant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="offer_redemptions", to="loyalty.tenant")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="offer_redemptions", to="loyalty.user")),
            ],
            options={
                "verbose_name": "Offer redemption",
                "verbose_name_plural": "Offer redemptions",
            },
        ),
        migrations.AddConstraint(
            model_name="offerredemption",
            constraint=models.UniqueConstraint(fields=("offer", "user"), name="uniq_offer_redemption"),
        ),
        migrations.AddIndex(
            model_name="offerredemption",
            index=models.Index(fields=["tenant", "user"], name="loyalty_offe_tenant__f7dc32_idx"),
        ),
        migrations.AddIndex(
            model_name="offerredemption",
            index=models.Index(fields=["tenant", "offer"], name="loyalty_offe_tenant__7bfc0c_idx"),
        ),
    ]
