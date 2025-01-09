from django.db import models
from django_prometheus.models import ExportModelOperationsMixin

from shared.django_apps.codecov.models import BaseCodecovModel

# Copied from `models.py` to avoid circular imports
REPORTS_APP_LABEL = "reports"


# This is a workaround for "over-long" index names suggested here:
# <https://code.djangoproject.com/ticket/31881#comment:1>
class LongIndex(models.Index):
    @property
    def max_name_length(self):
        return 63


class CompareCommit(
    ExportModelOperationsMixin("reports.compare_commitcomparison"), BaseCodecovModel
):
    base_commit = models.ForeignKey(
        "core.Commit", related_name="+", on_delete=models.CASCADE
    )
    compare_commit = models.ForeignKey(
        "core.Commit", related_name="+", on_delete=models.CASCADE
    )

    report_storage_path = models.CharField(null=True, max_length=150)
    patch_totals = models.JSONField(null=True)
    state = models.TextField()
    error = models.TextField(null=True)

    class Meta:
        app_label = REPORTS_APP_LABEL
        db_table = "compare_commitcomparison"
        indexes = [
            LongIndex(
                name="compare_commitcomparison_base_commit_id_cf53c1d9",
                fields=["base_commit_id"],
            ),
            LongIndex(
                name="compare_commitcomparison_compare_commit_id_3ea19610",
                fields=["compare_commit_id"],
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                name="unique_comparison_between_commit",
                fields=["base_commit_id", "compare_commit_id"],
            ),
        ]


class CompareFlag(
    ExportModelOperationsMixin("reports.compare_flagcomparison"), BaseCodecovModel
):
    commit_comparison = models.ForeignKey(CompareCommit, on_delete=models.CASCADE)
    repositoryflag = models.ForeignKey("RepositoryFlag", on_delete=models.CASCADE)

    head_totals = models.JSONField(null=True)
    base_totals = models.JSONField(null=True)
    patch_totals = models.JSONField(null=True)

    class Meta:
        app_label = REPORTS_APP_LABEL
        db_table = "compare_flagcomparison"
        indexes = [
            LongIndex(
                name="compare_flagcomparison_commit_comparison_id_88fa76fe",
                fields=["commit_comparison_id"],
            ),
            LongIndex(
                name="compare_flagcomparison_repositoryflag_id_1a562739",
                fields=["repositoryflag_id"],
            ),
        ]


class CompareComponent(
    ExportModelOperationsMixin("reports.compare_componentcomparison"), BaseCodecovModel
):
    commit_comparison = models.ForeignKey(CompareCommit, on_delete=models.CASCADE)
    component_id = models.TextField(max_length=100)

    head_totals = models.JSONField(null=True)
    base_totals = models.JSONField(null=True)
    patch_totals = models.JSONField(null=True)

    class Meta:
        app_label = REPORTS_APP_LABEL
        db_table = "compare_componentcomparison"
        indexes = [
            LongIndex(
                name="compare_componentcomparison_commit_comparison_id_1c103280",
                fields=["commit_comparison_id"],
            ),
            models.Index(
                name="component_comparison_component",
                fields=["commit_comparison_id", "component_id"],
            ),
        ]
