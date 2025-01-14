from django.contrib.postgres.fields import ArrayField
from django.db import models
from django_prometheus.models import ExportModelOperationsMixin

from shared.django_apps.codecov.models import BaseCodecovModel
from shared.labelanalysis import LabelAnalysisRequestState

# Added to avoid 'doesn't declare an explicit app_label and isn't in an application in INSTALLED_APPS' error\
# Needs to be called the same as the API app
LABELANALYSIS_APP_LABEL = "labelanalysis"


class LabelAnalysisRequest(
    ExportModelOperationsMixin("labelanalysis.label_analysis_request"), BaseCodecovModel
):
    base_commit = models.ForeignKey(
        "core.Commit", on_delete=models.CASCADE, related_name="label_requests_as_base"
    )
    head_commit = models.ForeignKey(
        "core.Commit", on_delete=models.CASCADE, related_name="label_requests_as_head"
    )
    requested_labels = ArrayField(models.TextField(), null=True)
    state_id = models.IntegerField(
        null=False, choices=LabelAnalysisRequestState.choices()
    )
    result = models.JSONField(null=True)
    processing_params = models.JSONField(null=True)

    class Meta:
        app_label = LABELANALYSIS_APP_LABEL
        db_table = "labelanalysis_labelanalysisrequest"


class LabelAnalysisProcessingError(
    ExportModelOperationsMixin("labelanalysis.label_analysis_processing_error"),
    BaseCodecovModel,
):
    label_analysis_request = models.ForeignKey(
        "LabelAnalysisRequest",
        related_name="errors",
        on_delete=models.CASCADE,
    )
    error_code = models.CharField(max_length=100)
    error_params = models.JSONField(default=dict)

    class Meta:
        app_label = LABELANALYSIS_APP_LABEL
        db_table = "labelanalysis_labelanalysisprocessingerror"
