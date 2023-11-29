from django.conf import settings
from django.db import models


class BaseModel(models.Model):
    """
    Base model for timeseries metrics. It provides a timestamp field which
    represents the time that the data sample was captured at and a few metadata
    fields that we can filter or group by to investigate issues or identify
    trends.

    This is the Timescale version. After data flows through both Postgres and
    Timescale for a time, we'll pick one.
    """

    class Meta:
        abstract = True

    timestamp = models.DateTimeField(null=False, primary_key=True)

    # github/codecov/worker
    repo_slug = models.TextField(null=True)
    # github/codecov
    owner_slug = models.TextField(null=True)
    # github/codecov/worker/a3cf8ced...
    commit_slug = models.TextField(null=True)

    def save(self, *args, **kwargs):
        if settings.TELEMETRY_TIMESCALE_DB:
            kwargs["using"] = settings.TELEMETRY_TIMESCALE_DB
            super().save(*args, **kwargs)


class SimpleMetric(BaseModel):
    """
    Model for the `telemetry_simple` table which houses many simple metrics.
    Rather than create a bespoke model, table, and db migration for each timer
    or quantity we want to measure, we put it in `telemetry_simple`.

    Examples could include `list_repos_duration_seconds` or `uploads_processed`

    This is the Timescale version. After data flows through both Postgres and
    Timescale for a time, we'll pick one.
    """

    class Meta(BaseModel.Meta):
        db_table = "telemetry_simple"
        indexes = [
            models.Index(
                fields=[
                    "name",
                    "timestamp",
                    "repo_slug",
                    "owner_slug",
                    "commit_slug",
                ],
            ),
        ]

    name = models.TextField(null=False)
    value = models.FloatField(null=False)
