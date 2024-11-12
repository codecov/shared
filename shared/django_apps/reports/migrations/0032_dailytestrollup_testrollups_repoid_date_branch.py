# Generated by Django 4.2.16 on 2024-11-11 19:18

from django.db import migrations, models

from shared.django_apps.migration_utils import (
    RiskyAddIndex,
)

"""
BEGIN;
--
-- Create index testrollups_repoid_date_branch on field(s) repoid, date, branch of model dailytestrollup
--
CREATE INDEX "testrollups_repoid_date_branch" ON "reports_dailytestrollups" ("repoid", "date", "branch");
COMMIT;
"""


class Migration(migrations.Migration):
    dependencies = [
        ("reports", "0031_lastcacherollupdate_and_more"),
    ]

    operations = [
        RiskyAddIndex(
            model_name="dailytestrollup",
            index=models.Index(
                fields=["repoid", "date", "branch"],
                name="testrollups_repoid_date_branch",
            ),
        ),
    ]
