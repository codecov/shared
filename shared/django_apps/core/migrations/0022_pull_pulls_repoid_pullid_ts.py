# Generated by Django 4.1.7 on 2023-04-24 18:59

from django.db import migrations, models

from shared.django_apps.migration_utils import RiskyAddIndex


class Migration(migrations.Migration):
    """
    BEGIN;
    --
    -- Create index pulls_repoid_pullid_ts on field(s) repository, pullid, updatestamp of model pull
    --
    CREATE INDEX "pulls_repoid_pullid_ts" ON "pulls" ("repoid", "pullid", "updatestamp");
    COMMIT;
    """

    dependencies = [
        ("core", "0021_pull_behind_by_pull_behind_by_commit"),
    ]

    operations = [
        RiskyAddIndex(
            model_name="pull",
            index=models.Index(
                fields=["repository", "pullid", "updatestamp"],
                name="pulls_repoid_pullid_ts",
            ),
        ),
    ]
