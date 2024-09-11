# Generated by Django 4.2.15 on 2024-09-09 20:02

import django.contrib.postgres.fields
import django.db.models.deletion
import psqlextra.backend.migrations.operations.add_default_partition
import psqlextra.backend.migrations.operations.create_partitioned_model
import psqlextra.manager.manager
import psqlextra.models.partitioned
import psqlextra.types
from django.db import migrations, models

"""
BEGIN;
--
-- Create partitioned model DailyTestRollup
--
CREATE TABLE "reports_dailytestrollups" ("id" bigint NOT NULL GENERATED BY DEFAULT AS IDENTITY, "created_at" timestamp with time zone NOT NULL, "updated_at" timestamp with time zone NOT NULL, "date" date NOT NULL, "repoid" integer NOT NULL, "branch" text NOT NULL, "fail_count" integer NOT NULL, "skip_count" integer NOT NULL, "pass_count" integer NOT NULL, "last_duration_seconds" double precision NOT NULL, "avg_duration_seconds" double precision NOT NULL, "latest_run" timestamp with time zone NOT NULL, "commits_where_fail" text[] NOT NULL, "test_id" text NOT NULL, PRIMARY KEY ("id", "date")) PARTITION BY RANGE ("date");
--
-- Creates default partition 'default' on DailyTestRollup
--
CREATE TABLE "reports_dailytestrollups_default" PARTITION OF "reports_dailytestrollups" DEFAULT;
--
-- Create constraint reports_dailytestrollups_repoid_date_branch_test on model dailytestrollup
--
ALTER TABLE "reports_dailytestrollups" ADD CONSTRAINT "reports_dailytestrollups_repoid_date_branch_test" UNIQUE ("repoid", "date", "branch", "test_id");
ALTER TABLE "reports_dailytestrollups" ADD CONSTRAINT "reports_dailytestrollups_test_id_bb017fbf_fk_reports_test_id" FOREIGN KEY ("test_id") REFERENCES "reports_test" ("id") DEFERRABLE INITIALLY DEFERRED;
CREATE INDEX "reports_dailytestrollups_test_id_bb017fbf" ON "reports_dailytestrollups" ("test_id");
CREATE INDEX "reports_dailytestrollups_test_id_bb017fbf_like" ON "reports_dailytestrollups" ("test_id" text_pattern_ops);
CREATE INDEX "dailytestrollups_repoid_date" ON "reports_dailytestrollups" ("repoid", "date");
COMMIT;
"""


class Migration(migrations.Migration):
    dependencies = [
        ("reports", "0022_reducederror_flake_testinstance_reduced_error_and_more"),
    ]

    operations = [
        psqlextra.backend.migrations.operations.create_partitioned_model.PostgresCreatePartitionedModel(
            name="DailyTestRollup",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("date", models.DateField()),
                ("repoid", models.IntegerField()),
                ("branch", models.TextField()),
                ("fail_count", models.IntegerField()),
                ("skip_count", models.IntegerField()),
                ("pass_count", models.IntegerField()),
                ("last_duration_seconds", models.FloatField()),
                ("avg_duration_seconds", models.FloatField()),
                ("latest_run", models.DateTimeField()),
                (
                    "commits_where_fail",
                    django.contrib.postgres.fields.ArrayField(
                        base_field=models.TextField(), size=None
                    ),
                ),
                (
                    "test",
                    models.ForeignKey(
                        db_column="test_id",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="daily_test_rollups",
                        to="reports.test",
                    ),
                ),
            ],
            options={
                "db_table": "reports_dailytestrollups",
                "indexes": [
                    models.Index(
                        fields=["repoid", "date"], name="dailytestrollups_repoid_date"
                    )
                ],
            },
            partitioning_options={
                "method": psqlextra.types.PostgresPartitioningMethod["RANGE"],
                "key": ["date"],
            },
            bases=(psqlextra.models.partitioned.PostgresPartitionedModel,),
            managers=[
                ("objects", psqlextra.manager.manager.PostgresManager()),
            ],
        ),
        psqlextra.backend.migrations.operations.add_default_partition.PostgresAddDefaultPartition(
            model_name="DailyTestRollup",
            name="default",
        ),
        migrations.AddConstraint(
            model_name="dailytestrollup",
            constraint=models.UniqueConstraint(
                fields=("repoid", "date", "branch", "test"),
                name="reports_dailytestrollups_repoid_date_branch_test",
            ),
        ),
    ]
