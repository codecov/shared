from datetime import datetime, timezone

from django.test import TestCase

from shared.django_apps.pg_telemetry.models import SimpleMetric as PgSimpleMetric
from shared.django_apps.ts_telemetry.models import SimpleMetric as TsSimpleMetric


class TestTsSimpleMetricModel(TestCase):
    """
    Test that we can create `TsSimpleMetric` records and that they are routed
    to a separate database from `PgSimpleMetric` records.
    """

    databases = {"default", "timeseries"}

    def test_create_simple_metric(self):
        timestamp = datetime.now().replace(tzinfo=timezone.utc)

        TsSimpleMetric.objects.create(
            name="bar",
            value=5.0,
            timestamp=timestamp,
            repo_slug="github/codecov/shared",
            owner_slug="github/codecov",
            commit_slug="github/codecov/shared/ae4ce5fc",
        )
        fetched = TsSimpleMetric.objects.get(timestamp=timestamp)

        # Assert that we got back the record we saved
        assert fetched.name == "bar"
        assert fetched.value == 5.0
        assert fetched.timestamp == timestamp
        assert fetched.repo_slug == "github/codecov/shared"
        assert fetched.owner_slug == "github/codecov"
        assert fetched.commit_slug == "github/codecov/shared/ae4ce5fc"

        # Assert that the record is only found in `TsSimpleMetric` and not
        # `PgSimpleMetric`
        fetched_from_pg = PgSimpleMetric.objects.filter(timestamp=timestamp).first()
        assert fetched_from_pg is None
