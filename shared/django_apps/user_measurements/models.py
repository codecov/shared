from django.db import models
from psqlextra.models import PostgresPartitionedModel
from psqlextra.types import PostgresPartitioningMethod

from shared.django_apps.codecov_auth.models import Owner
from shared.django_apps.core.models import Commit, Repository
from shared.django_apps.reports.models import ReportSession, ReportType


class UserMeasurement(PostgresPartitionedModel):
    class PartitioningMeta:
        method = PostgresPartitioningMethod.RANGE
        key = ["created_at"]

    class Meta:
        db_table_comment = "Store uploads on monthly partitions"

    id = models.BigAutoField(primary_key=True)
    repo = models.ForeignKey(
        Repository,
        on_delete=models.CASCADE,
        related_name="user_measurements",
    )
    commit = models.ForeignKey(
        Commit,
        on_delete=models.CASCADE,
        related_name="user_measurements",
    )
    upload = models.ForeignKey(
        ReportSession,
        on_delete=models.CASCADE,
        related_name="user_measurements",
    )
    owner = models.ForeignKey(
        Owner,
        on_delete=models.CASCADE,
        related_name="user_measurements",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    uploader_used = models.CharField()
    random_col = models.CharField(
        null=True, max_length=100, choices=ReportType.choices
    )
    private_repo = models.BooleanField()
    report_type = models.CharField(
        null=True, max_length=100, choices=ReportType.choices
    )

    class Meta:
        db_table = "user_measurements"
        indexes = [
            models.Index(fields=["owner"], name="i_owner"),
            models.Index(fields=["owner", "repo"], name="owner_repo"),
            models.Index(
                fields=["owner", "private_repo"],
                name="owner_private_repo",
            ),
            models.Index(
                fields=["owner", "private_repo", "report_type"],
                name="owner_private_repo_report_type",
            ),
        ]
