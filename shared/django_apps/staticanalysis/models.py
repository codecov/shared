from django.db import models
from django_prometheus.models import ExportModelOperationsMixin

from shared.django_apps.codecov.models import BaseCodecovModel
from shared.staticanalysis import StaticAnalysisSingleFileSnapshotState

# Added to avoid 'doesn't declare an explicit app_label and isn't in an application in INSTALLED_APPS' error\
# Needs to be called the same as the API app
STATICANALYSIS_APP_LABEL = "staticanalysis"


class StaticAnalysisSuite(
    ExportModelOperationsMixin("staticanalysis.static_analysis_suite"), BaseCodecovModel
):
    commit = models.ForeignKey("core.Commit", on_delete=models.CASCADE)

    class Meta:
        app_label = STATICANALYSIS_APP_LABEL
        db_table = "staticanalysis_staticanalysissuite"

        constraints = [
            models.UniqueConstraint(
                fields=["external_id"], name="staticanalysis_external_id_uniq"
            ),
        ]


class StaticAnalysisSingleFileSnapshot(
    ExportModelOperationsMixin("staticanalysis.static_analysis_single_file_snapshot"),
    BaseCodecovModel,
):
    repository = models.ForeignKey("core.Repository", on_delete=models.CASCADE)
    file_hash = models.UUIDField(null=False)
    content_location = models.TextField()
    state_id = models.IntegerField(
        choices=StaticAnalysisSingleFileSnapshotState.choices()
    )

    class Meta:
        app_label = STATICANALYSIS_APP_LABEL
        db_table = "staticanalysis_staticanalysissinglefilesnapshot"

        constraints = [
            models.UniqueConstraint(
                fields=["repository", "file_hash"], name="staticanalysis_repo_filehash"
            ),
        ]


class StaticAnalysisSuiteFilepath(
    ExportModelOperationsMixin("staticanalysis.static_analysis_suite_filepath"),
    BaseCodecovModel,
):
    analysis_suite = models.ForeignKey(
        StaticAnalysisSuite, on_delete=models.CASCADE, related_name="filepaths"
    )
    file_snapshot = models.ForeignKey(
        StaticAnalysisSingleFileSnapshot,
        on_delete=models.CASCADE,
        related_name="filepaths",
    )
    filepath = models.TextField()

    class Meta:
        app_label = STATICANALYSIS_APP_LABEL
        db_table = "staticanalysis_staticanalysissuitefilepath"

    @property
    def file_hash(self):
        # TODO: double check so serializer doesnt get N + 1 queries
        return self.file_snapshot.file_hash
