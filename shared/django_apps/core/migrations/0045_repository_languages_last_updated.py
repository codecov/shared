# Generated by Django 4.2.7 on 2024-01-11 05:32

from django.db import migrations

from shared.django_apps.core.models import DateTimeWithoutTZField
from shared.django_apps.migration_utils import RiskyAddField


class Migration(migrations.Migration):
    """
    BEGIN;
    --
    -- Add field languages_last_updated to repository
    --
    ALTER TABLE "repos" ADD COLUMN "languages_last_updated" timestamp NULL;
    COMMIT;
    """

    dependencies = [
        ("core", "0044_alter_repository_bundle_analysis_enabled_and_more"),
    ]

    operations = [
        RiskyAddField(
            model_name="repository",
            name="languages_last_updated",
            field=DateTimeWithoutTZField(blank=True, null=True),
        ),
    ]
