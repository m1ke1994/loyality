from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("loyalty", "0008_rule_targeting"),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name="loyaltyrule",
            unique_together=set(),
        ),
    ]
