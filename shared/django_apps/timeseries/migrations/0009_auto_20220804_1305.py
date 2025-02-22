# Generated by Django 3.2.12 on 2022-08-04 13:05

import datetime

from django.db import migrations

from shared.django_apps.core.models import DateTimeWithoutTZField


class Migration(migrations.Migration):
    """
    BEGIN;
    --
    -- Alter field created_at on dataset
    --
    --
    -- Alter field updated_at on dataset
    --
    COMMIT;
    """

    dependencies = [
        ("timeseries", "0008_auto_20220802_1838"),
    ]

    operations = [
        migrations.AlterField(
            model_name="dataset",
            name="created_at",
            field=DateTimeWithoutTZField(default=datetime.datetime.now, null=True),
        ),
        migrations.AlterField(
            model_name="dataset",
            name="updated_at",
            field=DateTimeWithoutTZField(default=datetime.datetime.now, null=True),
        ),
    ]
