import logging
import uuid

from django.contrib.postgres.fields import ArrayField
from django.db import models
from django_prometheus.models import ExportModelOperationsMixin
from psqlextra.models import PostgresPartitionedModel
from psqlextra.types import PostgresPartitioningMethod

from shared.django_apps.codecov.models import BaseCodecovModel, BaseModel
from shared.django_apps.reports.managers import CommitReportManager
from shared.django_apps.utils.config import should_write_data_to_storage_config_check
from shared.django_apps.utils.model_utils import ArchiveField
from shared.django_apps.utils.services import get_short_service_name
from shared.reports.enums import UploadState, UploadType
from shared.upload.constants import ci

log = logging.getLogger(__name__)

# Added to avoid 'doesn't declare an explicit app_label and isn't in an application in INSTALLED_APPS' error\
# Needs to be called the same as the API app
REPORTS_APP_LABEL = "reports"


class ReportType(models.TextChoices):
    COVERAGE = "coverage"
    TEST_RESULTS = "test_results"
    BUNDLE_ANALYSIS = "bundle_analysis"


class AbstractTotals(
    ExportModelOperationsMixin("reports.abstract_totals"), BaseCodecovModel
):
    branches = models.IntegerField()
    coverage = models.DecimalField(max_digits=8, decimal_places=5)
    hits = models.IntegerField()
    lines = models.IntegerField()
    methods = models.IntegerField()
    misses = models.IntegerField()
    partials = models.IntegerField()
    files = models.IntegerField()

    class Meta:
        abstract = True


class CommitReport(
    ExportModelOperationsMixin("reports.commit_report"), BaseCodecovModel
):
    class ReportType(models.TextChoices):
        COVERAGE = "coverage"
        TEST_RESULTS = "test_results"
        BUNDLE_ANALYSIS = "bundle_analysis"

    commit = models.ForeignKey(
        "core.Commit", related_name="reports", on_delete=models.CASCADE
    )
    code = models.CharField(null=True, max_length=100)
    report_type = models.CharField(
        null=True, max_length=100, choices=ReportType.choices
    )

    class Meta:
        app_label = REPORTS_APP_LABEL

    objects = CommitReportManager()


class ReportResults(
    ExportModelOperationsMixin("reports.report_results"), BaseCodecovModel
):
    class ReportResultsStates(models.TextChoices):
        PENDING = "pending"
        COMPLETED = "completed"
        ERROR = "error"

    report = models.OneToOneField(CommitReport, on_delete=models.CASCADE)
    state = models.TextField(null=True, choices=ReportResultsStates.choices)
    completed_at = models.DateTimeField(null=True)
    result = models.JSONField(default=dict)

    class Meta:
        app_label = REPORTS_APP_LABEL


class ReportDetails(
    ExportModelOperationsMixin("reports.report_details"), BaseCodecovModel
):
    report = models.OneToOneField(CommitReport, on_delete=models.CASCADE)
    _files_array = ArrayField(models.JSONField(), db_column="files_array", null=True)
    _files_array_storage_path = models.URLField(
        db_column="files_array_storage_path", null=True
    )

    class Meta:
        app_label = REPORTS_APP_LABEL

    def get_repository(self):
        return self.report.commit.repository

    def get_commitid(self):
        return self.report.commit.commitid

    def should_write_to_storage(self) -> bool:
        if (
            self.report is None
            or self.report.commit is None
            or self.report.commit.repository is None
            or self.report.commit.repository.author is None
        ):
            return False
        is_codecov_repo = self.report.commit.repository.author.username == "codecov"
        return should_write_data_to_storage_config_check(
            master_switch_key="report_details_files_array",
            is_codecov_repo=is_codecov_repo,
            repoid=self.report.commit.repository.repoid,
        )

    files_array = ArchiveField(
        should_write_to_storage_fn=should_write_to_storage,
        default_value_class=list,
    )


class ReportLevelTotals(AbstractTotals):
    report = models.OneToOneField(CommitReport, on_delete=models.CASCADE)

    class Meta:
        app_label = REPORTS_APP_LABEL


class UploadError(ExportModelOperationsMixin("reports.upload_error"), BaseCodecovModel):
    report_session = models.ForeignKey(
        "ReportSession",
        db_column="upload_id",
        related_name="errors",
        on_delete=models.CASCADE,
    )
    error_code = models.CharField(max_length=100)
    error_params = models.JSONField(default=dict)

    class Meta:
        app_label = REPORTS_APP_LABEL
        db_table = "reports_uploaderror"


class UploadFlagMembership(
    ExportModelOperationsMixin("reports.upload_flag_membership"), models.Model
):
    report_session = models.ForeignKey(
        "ReportSession", db_column="upload_id", on_delete=models.CASCADE
    )
    flag = models.ForeignKey("RepositoryFlag", on_delete=models.CASCADE)
    id = models.BigAutoField(primary_key=True)

    class Meta:
        app_label = REPORTS_APP_LABEL
        db_table = "reports_uploadflagmembership"


class RepositoryFlag(
    ExportModelOperationsMixin("reports.repository_flag"), BaseCodecovModel
):
    repository = models.ForeignKey(
        "core.Repository", related_name="flags", on_delete=models.CASCADE
    )
    flag_name = models.CharField(max_length=1024)
    deleted = models.BooleanField(null=True)

    class Meta:
        app_label = REPORTS_APP_LABEL


class ReportSession(
    ExportModelOperationsMixin("reports.report_session"), BaseCodecovModel
):
    # should be called Upload, but to do it we have to make the
    # constraints be manually named, which take a bit
    build_code = models.TextField(null=True)
    build_url = models.TextField(null=True)
    env = models.JSONField(null=True)
    flags = models.ManyToManyField(RepositoryFlag, through=UploadFlagMembership)
    job_code = models.TextField(null=True)
    name = models.CharField(null=True, max_length=100)
    provider = models.CharField(max_length=50, null=True)
    report = models.ForeignKey(
        "CommitReport", related_name="sessions", on_delete=models.CASCADE
    )
    state = models.CharField(max_length=100)
    storage_path = models.TextField()
    order_number = models.IntegerField(null=True)
    upload_type = models.CharField(max_length=100, default="uploaded")
    upload_extras = models.JSONField(default=dict)
    state_id = models.IntegerField(null=True, choices=UploadState.choices())
    upload_type_id = models.IntegerField(null=True, choices=UploadType.choices())

    class Meta:
        app_label = REPORTS_APP_LABEL
        db_table = "reports_upload"
        indexes = [
            models.Index(
                name="upload_report_type_idx",
                fields=["report_id", "upload_type"],
            ),
        ]

    @property
    def ci_url(self):
        if self.build_url:
            # build_url was saved in the database
            return self.build_url

        # otherwise we need to construct it ourself (if possible)
        build_url = ci.get(self.provider, {}).get("build_url")
        if not build_url:
            return
        repository = self.report.commit.repository
        data = {
            "service_short": get_short_service_name(repository.author.service),
            "owner": repository.author,
            "upload": self,
            "repo": repository,
            "commit": self.report.commit,
        }
        return build_url.format(**data)

    @property
    def flag_names(self):
        return [flag.flag_name for flag in self.flags.all()]


class UploadLevelTotals(AbstractTotals):
    report_session = models.OneToOneField(
        ReportSession, db_column="upload_id", on_delete=models.CASCADE
    )

    class Meta:
        app_label = REPORTS_APP_LABEL
        db_table = "reports_uploadleveltotals"


class Test(models.Model):
    # the reason we aren't using the regular primary key
    # in this case is because we want to be able to compute/predict
    # the primary key of a Test object ourselves in the processor
    # so we can easily do concurrent writes to the database
    # this is a hash of the repoid, name, testsuite and flags_hash
    id = models.TextField(primary_key=True)

    external_id = models.UUIDField(default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    repository = models.ForeignKey(
        "core.Repository",
        db_column="repoid",
        related_name="tests",
        on_delete=models.CASCADE,
    )
    name = models.TextField()
    testsuite = models.TextField()
    # this is a hash of the flags associated with this test
    # users will use flags to distinguish the same test being run
    # in a different environment
    # for example: the same test being run on windows vs. mac
    flags_hash = models.TextField()

    class Framework(models.TextChoices):
        PYTEST = "pytest"
        JEST = "jest"
        VITEST = "vitest"
        PHPUNIT = "phpunit"

    framework = models.CharField(max_length=100, choices=Framework.choices, null=True)

    computed_name = models.TextField(null=True)
    filename = models.TextField(null=True)

    class Meta:
        app_label = REPORTS_APP_LABEL
        db_table = "reports_test"
        constraints = [
            models.UniqueConstraint(
                fields=["repository", "name", "testsuite", "flags_hash"],
                name="reports_test_repoid_name_testsuite_flags_hash",
            ),
        ]


class TestInstance(BaseCodecovModel):
    test = models.ForeignKey(
        "Test",
        db_column="test_id",
        related_name="testinstances",
        on_delete=models.CASCADE,
    )

    class Outcome(models.TextChoices):
        FAILURE = "failure"
        SKIP = "skip"
        ERROR = "error"
        PASS = "pass"

    duration_seconds = models.FloatField(null=True)
    outcome = models.CharField(max_length=100, choices=Outcome.choices)
    upload = models.ForeignKey(
        "ReportSession",
        db_column="upload_id",
        related_name="testinstances",
        on_delete=models.CASCADE,
    )
    failure_message = models.TextField(null=True)

    branch = models.TextField(null=True)
    commitid = models.TextField(null=True)
    repoid = models.IntegerField(null=True)

    reduced_error = models.ForeignKey(
        "ReducedError",
        db_column="reduced_error_id",
        related_name="testinstances",
        on_delete=models.CASCADE,
        null=True,
    )

    class Meta:
        app_label = REPORTS_APP_LABEL
        db_table = "reports_testinstance"
        indexes = [
            models.Index(fields=["commitid", "repoid", "branch"]),
            models.Index(fields=["repoid", "created_at", "outcome"]),
        ]


class TestResultReportTotals(BaseCodecovModel):
    passed = models.IntegerField()
    skipped = models.IntegerField()
    failed = models.IntegerField()

    class TestResultsProcessingError(models.TextChoices):
        NO_SUCCESS = "no_success"

    error = models.CharField(
        null=True, max_length=100, choices=TestResultsProcessingError.choices
    )

    report = models.OneToOneField(CommitReport, on_delete=models.CASCADE)

    class Meta:
        app_label = REPORTS_APP_LABEL
        db_table = "reports_testresultreporttotals"


class ReducedError(BaseModel):
    message = models.TextField()
    repository = models.ForeignKey(
        "core.Repository",
        db_column="repoid",
        related_name="reduced_errors",
        on_delete=models.CASCADE,
        null=True,
    )

    class Meta:
        app_label = REPORTS_APP_LABEL
        db_table = "reports_reducederror"

        constraints = [
            models.UniqueConstraint(
                fields=["message", "repository"],
                name="reports_reducederror_message_constraint",
            ),
        ]


class Flake(models.Model):
    id = models.BigAutoField(primary_key=True)
    repository = models.ForeignKey(
        "core.Repository",
        db_column="repoid",
        related_name="flakes",
        on_delete=models.CASCADE,
    )
    test = models.ForeignKey(
        "Test", db_column="testid", related_name="flakes", on_delete=models.CASCADE
    )
    reduced_error = models.ForeignKey(
        "ReducedError",
        db_column="reduced_error_id",
        related_name="flakes",
        on_delete=models.CASCADE,
        null=True,
    )

    recent_passes_count = models.IntegerField()
    count = models.IntegerField()
    fail_count = models.IntegerField()
    start_date = models.DateTimeField()
    end_date = models.DateTimeField(null=True)

    class Meta:
        app_label = REPORTS_APP_LABEL
        db_table = "reports_flake"
        indexes = [
            models.Index(fields=["repository", "test", "reduced_error", "end_date"])
        ]


class DailyTestRollup(PostgresPartitionedModel, BaseModel):
    class PartitioningMeta:
        method = PostgresPartitioningMethod.RANGE
        key = ["date"]

    test = models.ForeignKey(
        "Test",
        db_column="test_id",
        related_name="daily_test_rollups",
        on_delete=models.CASCADE,
    )
    date = models.DateField()
    repoid = models.IntegerField()
    branch = models.TextField(null=True)

    fail_count = models.IntegerField()
    flaky_fail_count = models.IntegerField()
    skip_count = models.IntegerField()
    pass_count = models.IntegerField()
    last_duration_seconds = models.FloatField()
    avg_duration_seconds = models.FloatField()
    latest_run = models.DateTimeField()
    commits_where_fail = ArrayField(models.TextField())

    class Meta:
        app_label = REPORTS_APP_LABEL
        db_table = "reports_dailytestrollups"
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "repoid",
                    "date",
                    "branch",
                    "test",
                ],
                name="reports_dailytestrollups_repoid_date_branch_test",
            )
        ]
        indexes = [
            models.Index(
                fields=[
                    "repoid",
                    "date",
                ],
                name="dailytestrollups_repoid_date",
            )
        ]


class TestFlagBridge(models.Model):
    flag = models.ForeignKey(
        "RepositoryFlag",
        db_column="flag_id",
        related_name="test_flag_bridges",
        on_delete=models.CASCADE,
    )

    test = models.ForeignKey(
        "Test",
        db_column="test_id",
        related_name="test_flag_bridges",
        on_delete=models.CASCADE,
    )

    class Meta:
        app_label = REPORTS_APP_LABEL
        db_table = "reports_test_results_flag_bridge"
        constraints = [
            models.UniqueConstraint(
                fields=["flag", "test"],
                name="reports_test_results_flag_bridge_flag_test",
            )
        ]


class LastCacheRollupDate(models.Model):
    id = models.BigAutoField(primary_key=True)
    repository = models.ForeignKey(
        "core.Repository", db_column="repoid", on_delete=models.CASCADE
    )
    branch = models.TextField()
    last_rollup_date = models.DateField()

    class Meta:
        app_label = REPORTS_APP_LABEL
        db_table = "reports_lastrollupdate"
        constraints = [
            models.UniqueConstraint(
                fields=["repository", "branch"],
                name="reports_lastrollupdate_repoid_branch",
            )
        ]
