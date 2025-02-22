# Generated by Django 4.2.16 on 2024-11-18 19:15

from django.db import migrations

from shared.django_apps.migration_utils import RiskyRunSQL


class Migration(migrations.Migration):
    dependencies = [
        ("legacy_migrations", "0006_delete_many_owner_triggers"),
    ]

    operations = [
        RiskyRunSQL(
            """
            DROP TRIGGER IF EXISTS repo_cache_state_update ON repos;
            DROP FUNCTION IF EXISTS repo_cache_state_update();
            DROP TRIGGER IF EXISTS repo_yaml_update ON repos;
            DROP FUNCTION IF EXISTS repo_yaml_update();
            """,
            reverse_sql=migrations.RunSQL.noop,
        )
    ]
