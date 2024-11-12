# Generated by Django 4.2.16 on 2024-11-12 22:47

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("legacy_migrations", "0004_auto_20231024_1937"),
    ]

    # Moved the behavior in this trigger to the .save() method on Pull model

    operations = [
        migrations.RunSQL(
            """
                DROP TRIGGER IF EXISTS pulls_before_update_drop_flare ON pulls;
                DROP FUNCTION IF EXISTS pulls_drop_flare();
            """,
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
