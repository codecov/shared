# Generated by Django 4.2.15 on 2024-09-20 21:02

import django.db.models.deletion
from django.db import migrations, models

"""
BEGIN;
--
-- Create model TestFlagBridge
--
CREATE TABLE "reports_test_results_flag_bridge" ("id" bigint NOT NULL PRIMARY KEY GENERATED BY DEFAULT AS IDENTITY, "created_at" timestamp with time zone NOT NULL, "updated_at" timestamp with time zone NOT NULL, "flag" text NOT NULL, "repoid" integer NOT NULL, "test_id" text NOT NULL);
ALTER TABLE "reports_test_results_flag_bridge" ADD CONSTRAINT "reports_test_results_repoid_0fb14417_fk_repos_rep" FOREIGN KEY ("repoid") REFERENCES "repos" ("repoid") DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE "reports_test_results_flag_bridge" ADD CONSTRAINT "reports_test_results_test_id_48eb4c8e_fk_reports_t" FOREIGN KEY ("test_id") REFERENCES "reports_test" ("id") DEFERRABLE INITIALLY DEFERRED;
CREATE INDEX "reports_test_results_flag_bridge_repoid_0fb14417" ON "reports_test_results_flag_bridge" ("repoid");
CREATE INDEX "reports_test_results_flag_bridge_test_id_48eb4c8e" ON "reports_test_results_flag_bridge" ("test_id");
CREATE INDEX "reports_test_results_flag_bridge_test_id_48eb4c8e_like" ON "reports_test_results_flag_bridge" ("test_id" text_pattern_ops);
COMMIT;
"""


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0057_increment_version"),
        ("reports", "0025_dailytestrollup_flaky_fail_count"),
    ]

    operations = [
        migrations.CreateModel(
            name="TestFlagBridge",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("flag", models.TextField()),
                (
                    "repository",
                    models.ForeignKey(
                        db_column="repoid",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="test_flag_bridges",
                        to="core.repository",
                    ),
                ),
                (
                    "test",
                    models.ForeignKey(
                        db_column="test_id",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="test_flag_bridges",
                        to="reports.test",
                    ),
                ),
            ],
            options={
                "db_table": "reports_test_results_flag_bridge",
            },
        ),
    ]
