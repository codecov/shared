from django.contrib.postgres.fields import ArrayField
from django.db import models
from django_prometheus.models import ExportModelOperationsMixin

TA_TIMESERIES_APP_LABEL = "ta_timeseries"


class Testrun(ExportModelOperationsMixin("ta_timeseries.testrun"), models.Model):
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
        app_label = TA_TIMESERIES_APP_LABEL
        indexes = [
            models.Index(
                name="ta_ts__branch_i",
                fields=["repo_id", "branch", "timestamp"],
            ),
            models.Index(
                name="ta_ts__branch_test_i",
                fields=["repo_id", "branch", "test_id", "timestamp"],
            ),
            models.Index(
                name="ta_ts__test_id_i",
                fields=["repo_id", "test_id", "timestamp"],
            ),
            models.Index(
                name="ta_ts__commit_i",
                fields=["repo_id", "commit_sha", "timestamp"],
            ),
        ]


class TestrunBranchSummary(
    ExportModelOperationsMixin("ta_timeseries.testrun_branch_summary"),
    models.Model,
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
        app_label = TA_TIMESERIES_APP_LABEL
        db_table = "ta_timeseries_testrun_branch_summary_1day"
        managed = False


class TestrunSummary(
    ExportModelOperationsMixin("ta_timeseries.testrun_summary"),
    models.Model,
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
        app_label = TA_TIMESERIES_APP_LABEL
        db_table = "ta_timeseries_testrun_summary_1day"
        managed = False
