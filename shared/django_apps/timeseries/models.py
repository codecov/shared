from datetime import datetime, timedelta
from enum import Enum

import django.db.models as models
from django.contrib.postgres.fields import ArrayField
from django.utils import timezone
from django_prometheus.models import ExportModelOperationsMixin

from shared.django_apps.core.models import DateTimeWithoutTZField

TIMESERIES_APP_LABEL = "timeseries"


class Interval(Enum):
    INTERVAL_1_DAY = 1
    INTERVAL_7_DAY = 7
    INTERVAL_30_DAY = 30


class MeasurementName(Enum):
    COVERAGE = "coverage"
    FLAG_COVERAGE = "flag_coverage"
    COMPONENT_COVERAGE = "component_coverage"
    # For tracking the entire size of a bundle report by its name
    BUNDLE_ANALYSIS_REPORT_SIZE = "bundle_analysis_report_size"
    # For tracking the size of a category of assets of a bundle report by its name
    BUNDLE_ANALYSIS_JAVASCRIPT_SIZE = "bundle_analysis_javascript_size"
    BUNDLE_ANALYSIS_STYLESHEET_SIZE = "bundle_analysis_stylesheet_size"
    BUNDLE_ANALYSIS_FONT_SIZE = "bundle_analysis_font_size"
    BUNDLE_ANALYSIS_IMAGE_SIZE = "bundle_analysis_image_size"
    # For tracking individual asset size via its UUID
    BUNDLE_ANALYSIS_ASSET_SIZE = "bundle_analysis_asset_size"


class Measurement(ExportModelOperationsMixin("timeseries.measurement"), models.Model):
    # TimescaleDB requires that `timestamp` be part of every index (since data is
    # partitioned by `timestamp`).  Since an auto-incrementing primary key would
    # not satisfy this requirement we can make `timestamp` the primary key.
    # `timestamp` may not be unique though so we drop the uniqueness constraint in
    # a migration.
    timestamp = models.DateTimeField(null=False, primary_key=True)

    owner_id = models.BigIntegerField(null=False)
    repo_id = models.BigIntegerField(null=False)
    measurable_id = models.TextField(null=False)
    branch = models.TextField(null=True)

    # useful for updating a measurement if needed
    commit_sha = models.TextField(null=True)

    # the name of the measurement (i.e. "coverage")
    name = models.TextField(null=False, blank=False)
    value = models.FloatField(null=False)

    class Meta:
        app_label = TIMESERIES_APP_LABEL
        indexes = [
            # for querying measurements
            models.Index(
                fields=[
                    "owner_id",
                    "repo_id",
                    "measurable_id",
                    "branch",
                    "name",
                    "timestamp",
                ]
            ),
        ]
        constraints = [
            # for updating measurements
            models.UniqueConstraint(
                fields=[
                    "name",
                    "owner_id",
                    "repo_id",
                    "measurable_id",
                    "commit_sha",
                    "timestamp",
                ],
                name="timeseries_measurement_unique",
            ),
        ]


class MeasurementSummary(
    ExportModelOperationsMixin("timeseries.measurement_summary"), models.Model
):
    timestamp_bin = models.DateTimeField(primary_key=True)
    owner_id = models.BigIntegerField()
    repo_id = models.BigIntegerField()
    measurable_id = models.TextField()
    branch = models.TextField()
    name = models.TextField()
    value_avg = models.FloatField()
    value_max = models.FloatField()
    value_min = models.FloatField()
    value_count = models.FloatField()

    @classmethod
    def agg_by(cls, interval: Interval) -> models.Manager:
        model_classes = {
            Interval.INTERVAL_1_DAY: MeasurementSummary1Day,
            Interval.INTERVAL_7_DAY: MeasurementSummary7Day,
            Interval.INTERVAL_30_DAY: MeasurementSummary30Day,
        }

        model_class = model_classes.get(interval)
        if not model_class:
            raise ValueError(f"cannot aggregate by '{interval}'")
        return model_class.objects

    class Meta:
        app_label = TIMESERIES_APP_LABEL
        abstract = True
        # these are backed by TimescaleDB "continuous aggregates"
        # (materialized views)
        managed = False
        ordering = ["timestamp_bin"]


class MeasurementSummary1Day(MeasurementSummary):
    class Meta(MeasurementSummary.Meta):
        db_table = "timeseries_measurement_summary_1day"


# Timescale's origin for time buckets is Monday 2000-01-03
# Weekly aggregate bins will thus be Monday-Sunday
class MeasurementSummary7Day(MeasurementSummary):
    class Meta(MeasurementSummary.Meta):
        db_table = "timeseries_measurement_summary_7day"


# Timescale's origin for time buckets is 2000-01-03
# 30 day offsets will be aligned on that origin
class MeasurementSummary30Day(MeasurementSummary):
    class Meta(MeasurementSummary.Meta):
        db_table = "timeseries_measurement_summary_30day"


class Dataset(ExportModelOperationsMixin("timeseries.dataset"), models.Model):
    id = models.AutoField(primary_key=True)

    # this will likely correspond to a measurement name above
    name = models.TextField(null=False, blank=False)

    # not a true foreign key since repositories are in a
    # different database
    repository_id = models.IntegerField(null=False)

    # indicates whether the backfill task has completed for this dataset
    # TODO: We're not really using this field anymore as a backfill task takes very long for this to be populated when finished.
    # The solution would be to somehow have a celery task return when it's done, hence the TODO
    backfilled = models.BooleanField(null=False, default=False)

    created_at = DateTimeWithoutTZField(default=timezone.now, null=True)
    updated_at = DateTimeWithoutTZField(default=timezone.now, null=True)

    class Meta:
        app_label = TIMESERIES_APP_LABEL
        indexes = [
            models.Index(
                fields=[
                    "name",
                    "repository_id",
                ]
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "name",
                    "repository_id",
                ],
                name="name_repository_id_unique",
            ),
        ]

    def is_backfilled(self) -> bool:
        """
        Returns `False` for an hour after creation.

        TODO: this should eventually read `self.backfilled` which will be updated via the worker
        """
        if not self.created_at:
            return False
        return datetime.now() > self.created_at + timedelta(hours=1)


class Testrun(ExportModelOperationsMixin("timeseries.testrun"), models.Model):
    timestamp = models.DateTimeField(null=False, primary_key=True)

    test_id = models.BinaryField(null=False)

    name = models.TextField(null=True)
    classname = models.TextField(null=True)
    testsuite = models.TextField(null=True)
    computed_name = models.TextField(null=True)

    outcome = models.TextField(null=False)

    duration_seconds = models.FloatField(null=True)
    failure_message = models.TextField(null=True)
    framework = models.TextField(null=True)
    filename = models.TextField(null=True)

    repo_id = models.BigIntegerField(null=True)
    commit_sha = models.TextField(null=True)
    branch = models.TextField(null=True)

    flags = ArrayField(models.TextField(), null=True)
    upload_id = models.BigIntegerField(null=True)

    class Meta:
        app_label = TIMESERIES_APP_LABEL
        indexes = [
            models.Index(
                name="ts__repo_branch_time_i",
                fields=["repo_id", "branch", "timestamp"],
            ),
            models.Index(
                name="ts__repo_branch_test_time_i",
                fields=["repo_id", "branch", "test_id", "timestamp"],
            ),
            models.Index(
                name="ts__repo_test_id_time_i",
                fields=["repo_id", "test_id", "timestamp"],
            ),
            models.Index(
                name="ts__repo_commit_time_i",
                fields=["repo_id", "commit_sha", "timestamp"],
            ),
        ]


class TestrunBranchSummary(
    ExportModelOperationsMixin("timeseries.testrun_continuous_aggregate"), models.Model
):
    timestamp_bin = models.DateTimeField(primary_key=True)
    repo_id = models.IntegerField()
    branch = models.TextField()
    name = models.TextField()
    classname = models.TextField()
    testsuite = models.TextField()
    computed_name = models.TextField()
    failing_commits = models.IntegerField()
    avg_duration_seconds = models.FloatField()
    last_duration_seconds = models.FloatField()
    pass_count = models.IntegerField()
    fail_count = models.IntegerField()
    skip_count = models.IntegerField()
    flaky_fail_count = models.IntegerField()
    updated_at = models.DateTimeField()
    flags = ArrayField(models.TextField(), null=True)

    class Meta:
        app_label = TIMESERIES_APP_LABEL
        db_table = "timeseries_testrun_branch_summary_1day"
        managed = False


class TestrunSummary(
    ExportModelOperationsMixin("timeseries.testrun_continuous_aggregate"), models.Model
):
    timestamp_bin = models.DateTimeField(primary_key=True)
    repo_id = models.IntegerField()
    name = models.TextField()
    classname = models.TextField()
    testsuite = models.TextField()
    computed_name = models.TextField()
    failing_commits = models.IntegerField()
    avg_duration_seconds = models.FloatField()
    last_duration_seconds = models.FloatField()
    pass_count = models.IntegerField()
    fail_count = models.IntegerField()
    skip_count = models.IntegerField()
    flaky_fail_count = models.IntegerField()
    updated_at = models.DateTimeField()
    flags = ArrayField(models.TextField(), null=True)

    class Meta:
        app_label = TIMESERIES_APP_LABEL
        db_table = "timeseries_testrun_summary_1day"
        managed = False
