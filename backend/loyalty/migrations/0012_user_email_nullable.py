from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("loyalty", "0011_alter_auditlog_options_alter_coupon_options_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="user",
            name="email",
            field=models.EmailField(blank=True, null=True, verbose_name="Email"),
        ),
    ]
