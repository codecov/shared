# Generated by Django 4.1.7 on 2023-05-05 13:23

from django.conf import settings
from django.db import migrations, models

from shared.django_apps.migration_utils import RiskyAddConstraint, RiskyAddIndex


class Migration(migrations.Migration):
    """
    BEGIN;
    --
    -- Alter field measurable_id on measurement
    --
    ALTER TABLE "timeseries_measurement" ALTER COLUMN "measurable_id" SET NOT NULL;
    --
    -- Remove index timeseries__owner_i_2cc713_idx from measurement
    --
    DROP INDEX IF EXISTS "timeseries__owner_i_2cc713_idx";
    --
    -- Create index timeseries__owner_i_08d6fe_idx on field(s) owner_id, repo_id, measurable_id, branch, name, timestamp of model measurement
    --
    CREATE INDEX "timeseries__owner_i_08d6fe_idx" ON "timeseries_measurement" ("owner_id", "repo_id", "measurable_id", "branch", "name", "timestamp");
    --
    -- Create constraint timeseries_measurement_unique on model measurement
    --
    ALTER TABLE "timeseries_measurement" ADD CONSTRAINT "timeseries_measurement_unique" UNIQUE ("name", "owner_id", "repo_id", "measurable_id", "commit_sha", "timestamp");
    --
    -- Raw SQL operation
    --

    drop materialized view timeseries_measurement_summary_1day;
    create materialized view timeseries_measurement_summary_1day
    with (timescaledb.continuous) as
    select
        owner_id,
        repo_id,
        measurable_id,
        branch,
        name,
        time_bucket(interval '1 days', timestamp) as timestamp_bin,
        avg(value) as value_avg,
        max(value) as value_max,
        min(value) as value_min,
        count(value) as value_count
    from timeseries_measurement
    group by
        owner_id, repo_id, measurable_id, branch, name, timestamp_bin
    with no data;
    select add_continuous_aggregate_policy(
        'timeseries_measurement_summary_1day',
        start_offset => NULL,
        end_offset => NULL,
        schedule_interval => INTERVAL '1 h'
    );

    --
    -- Raw SQL operation
    --

    drop materialized view timeseries_measurement_summary_7day;
    create materialized view timeseries_measurement_summary_7day
    with (timescaledb.continuous) as
    select
        owner_id,
        repo_id,
        measurable_id,
        branch,
        name,
        time_bucket(interval '7 days', timestamp) as timestamp_bin,
        avg(value) as value_avg,
        max(value) as value_max,
        min(value) as value_min,
        count(value) as value_count
    from timeseries_measurement
    group by
        owner_id, repo_id, measurable_id, branch, name, timestamp_bin
    with no data;
    select add_continuous_aggregate_policy(
        'timeseries_measurement_summary_7day',
        start_offset => NULL,
        end_offset => NULL,
        schedule_interval => INTERVAL '1 h'
    );

    --
    -- Raw SQL operation
    --

    drop materialized view timeseries_measurement_summary_30day;
    create materialized view timeseries_measurement_summary_30day
    with (timescaledb.continuous) as
    select
        owner_id,
        repo_id,
        measurable_id,
        branch,
        name,
        time_bucket(interval '30 days', timestamp) as timestamp_bin,
        avg(value) as value_avg,
        max(value) as value_max,
        min(value) as value_min,
        count(value) as value_count
    from timeseries_measurement
    group by
        owner_id, repo_id, measurable_id, branch, name, timestamp_bin
    with no data;
    select add_continuous_aggregate_policy(
        'timeseries_measurement_summary_30day',
        start_offset => NULL,
        end_offset => NULL,
        schedule_interval => INTERVAL '1 h'
    );

    --
    -- Raw SQL operation
    --

    alter materialized view timeseries_measurement_summary_1day set (timescaledb.materialized_only = true);

    --
    -- Raw SQL operation
    --

    alter materialized view timeseries_measurement_summary_7day set (timescaledb.materialized_only = true);

    --
    -- Raw SQL operation
    --

    alter materialized view timeseries_measurement_summary_30day set (timescaledb.materialized_only = true);

    COMMIT;
    """

    dependencies = [
        ("timeseries", "0012_auto_20230501_1929"),
    ]

    operations = (
        [
            migrations.AlterField(
                model_name="measurement",
                name="measurable_id",
                field=models.TextField(),
            ),
            migrations.RemoveIndex(
                model_name="measurement",
                name="timeseries__owner_i_2cc713_idx",
            ),
            RiskyAddIndex(
                model_name="measurement",
                index=models.Index(
                    fields=[
                        "owner_id",
                        "repo_id",
                        "measurable_id",
                        "branch",
                        "name",
                        "timestamp",
                    ],
                    name="timeseries__owner_i_08d6fe_idx",
                ),
            ),
            RiskyAddConstraint(
                model_name="measurement",
                constraint=models.UniqueConstraint(
                    fields=(
                        "name",
                        "owner_id",
                        "repo_id",
                        "measurable_id",
                        "commit_sha",
                        "timestamp",
                    ),
                    name="timeseries_measurement_unique",
                ),
            ),
        ]
        + [
            migrations.RunSQL(
                f"""
                drop materialized view timeseries_measurement_summary_{days}day;
                create materialized view timeseries_measurement_summary_{days}day
                with (timescaledb.continuous) as
                select
                    owner_id,
                    repo_id,
                    measurable_id,
                    branch,
                    name,
                    time_bucket(interval '{days} days', timestamp) as timestamp_bin,
                    avg(value) as value_avg,
                    max(value) as value_max,
                    min(value) as value_min,
                    count(value) as value_count
                from timeseries_measurement
                group by
                    owner_id, repo_id, measurable_id, branch, name, timestamp_bin
                with no data;
                select add_continuous_aggregate_policy(
                    'timeseries_measurement_summary_{days}day',
                    start_offset => NULL,
                    end_offset => NULL,
                    schedule_interval => INTERVAL '1 h'
                );
                """
            )
            for days in [1, 7, 30]
        ]
        + [
            migrations.RunSQL(
                f"""
                alter materialized view timeseries_measurement_summary_{days}day set (timescaledb.materialized_only = true);
                """
            )
            for days in [1, 7, 30]
            if not settings.TIMESERIES_REAL_TIME_AGGREGATES
        ]
    )
