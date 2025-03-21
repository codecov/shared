# Generated by Django 4.2.16 on 2025-02-06 15:02

import django.contrib.postgres.fields
import django_prometheus.models
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        (
            "timeseries",
            "0014_remove_measurement_timeseries_measurement_flag_unique_and_more",
        ),
    ]

    operations = [
        migrations.CreateModel(
            name="Testrun",
            fields=[
                ("timestamp", models.DateTimeField(primary_key=True, serialize=False)),
                ("repo_id", models.BigIntegerField()),
                ("test_id", models.BinaryField()),
                ("testsuite", models.TextField(null=True)),
                ("classname", models.TextField(null=True)),
                ("name", models.TextField(null=True)),
                ("computed_name", models.TextField(null=True)),
                ("outcome", models.TextField()),
                ("duration_seconds", models.FloatField(null=True)),
                ("failure_message", models.TextField(null=True)),
                ("framework", models.TextField(null=True)),
                ("filename", models.TextField(null=True)),
                ("commit_sha", models.TextField(null=True)),
                ("branch", models.TextField(null=True)),
                (
                    "flags",
                    django.contrib.postgres.fields.ArrayField(
                        base_field=models.TextField(), null=True, size=None
                    ),
                ),
                ("upload_id", models.BigIntegerField(null=True)),
            ],
            bases=(
                django_prometheus.models.ExportModelOperationsMixin(
                    "timeseries.testrun"
                ),
                models.Model,
            ),
        ),
        migrations.RunSQL(
            "ALTER TABLE timeseries_testrun DROP CONSTRAINT timeseries_testrun_pkey;",
            reverse_sql="",
        ),
        migrations.RunSQL(
            "SELECT create_hypertable('timeseries_testrun', 'timestamp');",
            reverse_sql="",
        ),
        migrations.AddIndex(
            model_name="testrun",
            index=models.Index(
                fields=[
                    "repo_id",
                    "branch",
                    "timestamp",
                ],
                name="ts__repo_branch_time_i",
            ),
        ),
        migrations.AddIndex(
            model_name="testrun",
            index=models.Index(
                fields=["repo_id", "branch", "test_id", "timestamp"],
                name="ts__repo_branch_test_time_i",
            ),
        ),
        migrations.AddIndex(
            model_name="testrun",
            index=models.Index(
                fields=["repo_id", "test_id", "timestamp"],
                name="ts__repo_test_time_i",
            ),
        ),
        migrations.AddIndex(
            model_name="testrun",
            index=models.Index(
                fields=["repo_id", "commit_sha", "timestamp"],
                name="ts__repo_commit_time_i",
            ),
        ),
        migrations.RunSQL(
            """
            CREATE OR REPLACE FUNCTION array_merge_dedup(anyarray, anyarray)
            RETURNS anyarray LANGUAGE sql IMMUTABLE AS $$
                SELECT array_agg(DISTINCT x)
                FROM (
                    SELECT unnest($1) as x
                    UNION
                    SELECT unnest($2)
                ) s;
            $$;
            CREATE AGGREGATE array_merge_dedup_agg(anyarray) (
                SFUNC = array_merge_dedup,
                STYPE = anyarray,
                INITCOND = '{}'
            );
            """,
            reverse_sql="""
            DROP AGGREGATE array_merge_dedup_agg(anyarray);
            DROP FUNCTION array_merge_dedup(anyarray, anyarray);
            """,
        ),
    ]
