from django.db import models
from psqlextra.models import PostgresPartitionedModel
from psqlextra.types import PostgresPartitioningMethod

from shared.django_apps.reports.models import ReportType


class UserMeasurement(PostgresPartitionedModel):
    class PartitioningMeta:
        method = PostgresPartitioningMethod.RANGE
        key = ["created_at"]

    id = models.BigAutoField(primary_key=True)
    repo_id = models.IntegerField(null=True)
    commit_id = models.IntegerField(null=True)
    upload_id = models.IntegerField(null=True)
    owner_id = models.IntegerField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    uploader_used = models.CharField()
    private_repo = models.BooleanField()
    report_type = models.CharField(
        null=True, max_length=100, choices=ReportType.choices
    )

    class Meta:
        db_table = "user_measurements"
        indexes = [
            models.Index(fields=["owner_id"], name="i_owner"),
            models.Index(fields=["owner_id", "repo_id"], name="owner_repo"),
            models.Index(
                fields=["owner_id", "private_repo"],
                name="owner_private_repo",
            ),
            models.Index(
                fields=["owner_id", "private_repo", "report_type"],
                name="owner_private_repo_report_type",
            ),
        ]
