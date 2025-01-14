from django.db import models
from django_prometheus.models import ExportModelOperationsMixin

from shared.django_apps.codecov.models import BaseCodecovModel

# Added to avoid 'doesn't declare an explicit app_label and isn't in an application in INSTALLED_APPS' error\
# Needs to be called the same as the API app
PROFILING_APP_LABEL = "profiling"


class ProfilingCommit(
    ExportModelOperationsMixin("profiling.profiling_commit"), BaseCodecovModel
):
    last_joined_uploads_at = models.DateTimeField(null=True)
    environment = models.CharField(max_length=100, null=True)
    last_summarized_at = models.DateTimeField(null=True)
    joined_location = models.TextField(null=True)
    summarized_location = models.TextField(null=True)
    version_identifier = models.TextField()
    repository = models.ForeignKey(
        "core.Repository",
        db_column="repoid",
        on_delete=models.CASCADE,
        related_name="profilings",
    )
    commit_sha = models.TextField(null=True)
    code = models.TextField(null=True)

    class Meta:
        app_label = PROFILING_APP_LABEL
        db_table = "profiling_profilingcommit"

        constraints = [
            models.UniqueConstraint(
                fields=["repository", "code"], name="uniquerepocode"
            )
        ]

    def __str__(self):
        return f"ProfilingCommit<{self.version_identifier} at {self.repository}>"


class ProfilingUpload(
    ExportModelOperationsMixin("profiling.profiling_upload"), BaseCodecovModel
):
    raw_upload_location = models.TextField()
    profiling_commit = models.ForeignKey(
        ProfilingCommit, on_delete=models.CASCADE, related_name="uploads"
    )
    normalized_at = models.DateTimeField(null=True)
    normalized_location = models.TextField(null=True)

    class Meta:
        app_label = PROFILING_APP_LABEL
        db_table = "profiling_profilingupload"
