# Generated by Django 4.2.11 on 2024-06-20 18:21

import django.db.models.deletion
from django.db import migrations, models

from shared.django_apps.migration_utils import RiskyAddField

"""
BEGIN;
--
-- Create model ReducedError
--
CREATE TABLE "reports_reducederror" ("id" bigint NOT NULL PRIMARY KEY GENERATED BY DEFAULT AS IDENTITY, "created_at" timestamp with time zone NOT NULL, "updated_at" timestamp with time zone NOT NULL, "message" text NOT NULL, "repoid" integer NULL);
--
-- Create model Flake
--
CREATE TABLE "reports_flake" ("id" bigint NOT NULL PRIMARY KEY GENERATED BY DEFAULT AS IDENTITY, "created_at" timestamp with time zone NOT NULL, "updated_at" timestamp with time zone NOT NULL, "recent_passes_count" integer NOT NULL, "count" integer NOT NULL, "fail_count" integer NOT NULL, "start_date" timestamp with time zone NOT NULL, "end_date" timestamp with time zone NULL, "reduced_error_id" bigint NULL, "repoid" integer NOT NULL, "testid" text NOT NULL);
--
-- Add field reduced_error to testinstance
--
ALTER TABLE "reports_testinstance" ADD COLUMN "reduced_error_id" bigint NULL CONSTRAINT "reports_testinstance_reduced_error_id_f90c8b72_fk_reports_r" REFERENCES "reports_reducederror"("id") DEFERRABLE INITIALLY DEFERRED; SET CONSTRAINTS "reports_testinstance_reduced_error_id_f90c8b72_fk_reports_r" IMMEDIATE;
--
-- Create constraint reports_reducederror_message_constraint on model reducederror
--
ALTER TABLE "reports_reducederror" ADD CONSTRAINT "reports_reducederror_message_constraint" UNIQUE ("message", "repoid");
--
-- Create index reports_fla_repoid_69b787_idx on field(s) repository, test, reduced_error, end_date of model flake
--
CREATE INDEX "reports_fla_repoid_69b787_idx" ON "reports_flake" ("repoid", "testid", "reduced_error_id", "end_date");
ALTER TABLE "reports_reducederror" ADD CONSTRAINT "reports_reducederror_repoid_3c055705_fk_repos_repoid" FOREIGN KEY ("repoid") REFERENCES "repos" ("repoid") DEFERRABLE INITIALLY DEFERRED;
CREATE INDEX "reports_reducederror_repoid_3c055705" ON "reports_reducederror" ("repoid");
ALTER TABLE "reports_flake" ADD CONSTRAINT "reports_flake_reduced_error_id_1d102637_fk_reports_r" FOREIGN KEY ("reduced_error_id") REFERENCES "reports_reducederror" ("id") DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE "reports_flake" ADD CONSTRAINT "reports_flake_repoid_1454c21c_fk_repos_repoid" FOREIGN KEY ("repoid") REFERENCES "repos" ("repoid") DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE "reports_flake" ADD CONSTRAINT "reports_flake_testid_9873bd1c_fk_reports_test_id" FOREIGN KEY ("testid") REFERENCES "reports_test" ("id") DEFERRABLE INITIALLY DEFERRED;
CREATE INDEX "reports_flake_reduced_error_id_1d102637" ON "reports_flake" ("reduced_error_id");
CREATE INDEX "reports_flake_repoid_1454c21c" ON "reports_flake" ("repoid");
CREATE INDEX "reports_flake_testid_9873bd1c" ON "reports_flake" ("testid");
CREATE INDEX "reports_flake_testid_9873bd1c_like" ON "reports_flake" ("testid" text_pattern_ops);
CREATE INDEX "reports_testinstance_reduced_error_id_f90c8b72" ON "reports_testinstance" ("reduced_error_id");
COMMIT;
"""


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0052_increment_version"),
        ("reports", "0021_remove_testinstance_flaky_status_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="ReducedError",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("message", models.TextField()),
                (
                    "repository",
                    models.ForeignKey(
                        db_column="repoid",
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="reduced_errors",
                        to="core.repository",
                    ),
                ),
            ],
            options={
                "db_table": "reports_reducederror",
            },
        ),
        migrations.CreateModel(
            name="Flake",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("recent_passes_count", models.IntegerField()),
                ("count", models.IntegerField()),
                ("fail_count", models.IntegerField()),
                ("start_date", models.DateTimeField()),
                ("end_date", models.DateTimeField(null=True)),
                (
                    "reduced_error",
                    models.ForeignKey(
                        db_column="reduced_error_id",
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="flakes",
                        to="reports.reducederror",
                    ),
                ),
                (
                    "repository",
                    models.ForeignKey(
                        db_column="repoid",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="flakes",
                        to="core.repository",
                    ),
                ),
                (
                    "test",
                    models.ForeignKey(
                        db_column="testid",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="flakes",
                        to="reports.test",
                    ),
                ),
            ],
            options={
                "db_table": "reports_flake",
            },
        ),
        RiskyAddField(
            model_name="testinstance",
            name="reduced_error",
            field=models.ForeignKey(
                db_column="reduced_error_id",
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="testinstances",
                to="reports.reducederror",
            ),
        ),
        migrations.AddConstraint(
            model_name="reducederror",
            constraint=models.UniqueConstraint(
                fields=("message", "repository"),
                name="reports_reducederror_message_constraint",
            ),
        ),
        migrations.AddIndex(
            model_name="flake",
            index=models.Index(
                fields=["repository", "test", "reduced_error", "end_date"],
                name="reports_fla_repoid_69b787_idx",
            ),
        ),
    ]
