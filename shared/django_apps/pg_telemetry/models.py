from django.conf import settings
from django.db import models


class BaseModel(models.Model):
    """
    Base model for timeseries metrics. It provides a timestamp field which
    represents the time that the data sample was captured at and a few metadata
    fields that we can filter or group by to investigate issues or identify
    trends.

    This is the Postgres version. After data flows through both Postgres and
    Timescale for a time, we'll pick one.
    """

    class Meta:
        abstract = True

    timestamp = models.DateTimeField(null=False, primary_key=True)

    repo_id = models.BigIntegerField(null=True)
    owner_id = models.BigIntegerField(null=True)
    commit_id = models.BigIntegerField(null=True)

    def save(self, *args, **kwargs):
        if settings.TELEMETRY_VANILLA_DB:
            kwargs["using"] = settings.TELEMETRY_VANILLA_DB
            super().save(*args, **kwargs)


class SimpleMetric(BaseModel):
    """
    Model for the `telemetry_simple` table which houses many simple metrics.
    Rather than create a bespoke model, table, and db migration for each timer
    or quantity we want to measure, we put it in `telemetry_simple`.

    Examples could include `list_repos_duration_seconds` or `uploads_processed`

    This is the Postgres version. After data flows through both Postgres and
    Timescale for a time, we'll pick one.
    """

    class Meta(BaseModel.Meta):
        db_table = "telemetry_simple"
        indexes = [
            models.Index(
                fields=[
                    "name",
                    "timestamp",
                    "repo_id",
                    "owner_id",
                    "commit_id",
                ],
            ),
        ]

    name = models.TextField(null=False)
    value = models.FloatField(null=False)
