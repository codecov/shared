from django.db import models
from django_prometheus.models import ExportModelOperationsMixin

from shared.django_apps.codecov.models import BaseCodecovModel
from shared.django_apps.core.models import Commit
from shared.django_apps.reports.models import RepositoryFlag

# Added to avoid 'doesn't declare an explicit app_label and isn't in an application in INSTALLED_APPS' error\
# Needs to be called the same as the API app
COMPARE_APP_LABEL = "compare"


class CommitComparison(
    ExportModelOperationsMixin("compare.commit_comparison"), BaseCodecovModel
):
    class CommitComparisonStates(models.TextChoices):
        PENDING = "pending"
        ERROR = "error"
        PROCESSED = "processed"

    class CommitComparisonErrors(models.TextChoices):
        MISSING_BASE_REPORT = "missing_base_report"
        MISSING_HEAD_REPORT = "missing_head_report"

    base_commit = models.ForeignKey(
        Commit, on_delete=models.CASCADE, related_name="base_commit_comparisons"
    )
    compare_commit = models.ForeignKey(
        Commit, on_delete=models.CASCADE, related_name="compare_commit_comparisons"
    )
    state = models.TextField(
        choices=CommitComparisonStates.choices, default=CommitComparisonStates.PENDING
    )
    error = models.TextField(choices=CommitComparisonErrors.choices, null=True)
    report_storage_path = models.CharField(max_length=150, null=True, blank=True)
    patch_totals = models.JSONField(null=True)

    class Meta:
        app_label = COMPARE_APP_LABEL
        db_table = "compare_commitcomparison"

        constraints = [
            models.UniqueConstraint(
                name="unique_comparison_between_commit",
                fields=["base_commit", "compare_commit"],
            )
        ]

    @property
    def is_processed(self):
        return self.state == CommitComparison.CommitComparisonStates.PROCESSED


class FlagComparison(
    ExportModelOperationsMixin("compare.flag_comparison"), BaseCodecovModel
):
    commit_comparison = models.ForeignKey(
        CommitComparison, on_delete=models.CASCADE, related_name="flag_comparisons"
    )
    repositoryflag = models.ForeignKey(
        RepositoryFlag, on_delete=models.CASCADE, related_name="flag_comparisons"
    )
    head_totals = models.JSONField(null=True)
    base_totals = models.JSONField(null=True)
    patch_totals = models.JSONField(null=True)

    class Meta:
        app_label = COMPARE_APP_LABEL
        db_table = "compare_flagcomparison"


class ComponentComparison(
    ExportModelOperationsMixin("compare.component_comparison"), BaseCodecovModel
):
    commit_comparison = models.ForeignKey(
        CommitComparison, on_delete=models.CASCADE, related_name="component_comparisons"
    )
    component_id = models.TextField(null=False, blank=False)
    head_totals = models.JSONField(null=True)
    base_totals = models.JSONField(null=True)
    patch_totals = models.JSONField(null=True)

    class Meta:
        app_label = COMPARE_APP_LABEL
        db_table = "compare_componentcomparison"

        indexes = [
            models.Index(
                fields=["commit_comparison_id", "component_id"],
                name="component_comparison_component",
            ),
        ]
