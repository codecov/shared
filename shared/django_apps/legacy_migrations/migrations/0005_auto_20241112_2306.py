# Generated by Django 4.2.16 on 2024-11-12 23:06

from django.db import migrations

from shared.django_apps.migration_utils import RiskyRunSQL

class Migration(migrations.Migration):

    dependencies = [
        ('legacy_migrations', '0004_auto_20231024_1937'),
    ]

    operations = [
        RiskyRunSQL(
            """
            DROP TRIGGER IF EXISTS branch_update ON branches;
            DROP FUNCTION IF EXISTS branches_update();
            """
        ),
    ]
