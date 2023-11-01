# Generated by Django 4.2.6 on 2023-11-01 20:53
# Modified by hand to suit timeseries data

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="SimpleMetric",
            fields=[
                ("timestamp", models.DateTimeField(primary_key=True, serialize=False)),
                ("repo_slug", models.TextField(null=True)),
                ("owner_slug", models.TextField(null=True)),
                ("commit_slug", models.TextField(null=True)),
                ("name", models.TextField()),
                ("value", models.FloatField()),
            ],
            options={
                "db_table": "telemetry_simple",
                "abstract": False,
            },
        ),
        # Django wants us to have a primary key. Closest we have is `timestamp`,
        # but it isn't necessarily unique, so we drop the pkey constraint.
        migrations.RunSQL(
            "ALTER TABLE telemetry_simple DROP CONSTRAINT telemetry_simple_pkey;",
            reverse_sql="",
        ),
        migrations.AddIndex(
            model_name="SimpleMetric",
            index=models.Index(
                fields=[
                    "name",
                    "timestamp",
                    "repo_slug",
                    "owner_slug",
                    "commit_slug",
                ],
                name="telemetry_s_name_498f66_idx",
            ),
        ),
        # Convert `telemetry_simple` to a hypertable
        migrations.RunSQL(
            "SELECT create_hypertable('telemetry_simple', 'timestamp');",
            reverse_sql="",
        ),
    ]

    if settings.TEST:
        # Skip steps that complicate tests
        operations = [operations[0], operations[2]]
