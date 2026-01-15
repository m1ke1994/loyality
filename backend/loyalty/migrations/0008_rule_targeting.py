from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("loyalty", "0007_offer_redemption"),
    ]

    operations = [
        migrations.AddField(
            model_name="loyaltyrule",
            name="applies_to_all",
            field=models.BooleanField(default=True, verbose_name="Applies to all clients"),
        ),
        migrations.CreateModel(
            name="RuleTarget",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("rule", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="targets", to="loyalty.loyaltyrule")),
                ("tenant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="rule_targets", to="loyalty.tenant")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="rule_targets", to="loyalty.user")),
            ],
            options={
                "verbose_name": "Rule target",
                "verbose_name_plural": "Rule targets",
            },
        ),
        migrations.AddConstraint(
            model_name="ruletarget",
            constraint=models.UniqueConstraint(fields=("rule", "user"), name="uniq_rule_target"),
        ),
        migrations.AddIndex(
            model_name="ruletarget",
            index=models.Index(fields=["tenant", "user"], name="loyalty_rule_tenant__a870a1_idx"),
        ),
        migrations.AddIndex(
            model_name="ruletarget",
            index=models.Index(fields=["tenant", "rule"], name="loyalty_rule_tenant__f28a35_idx"),
        ),
    ]
