from datetime import datetime, timezone

from django.test import TestCase

from shared.django_apps.pg_telemetry.models import SimpleMetric as PgSimpleMetric


class TestPgSimpleMetricModel(TestCase):
    """
    Test that we can create `PgSimpleMetric` records and that they are routed
    to a separate database from `TsSimpleMetric` records.
    """

    databases = {"default", "timeseries"}

    def test_create_simple_metric(self):
        timestamp = datetime.now().replace(tzinfo=timezone.utc)

        PgSimpleMetric.objects.create(
            name="foo",
            value=3.0,
            timestamp=timestamp,
            repo_id=1,
            owner_id=2,
            commit_id=3,
        )
        fetched = PgSimpleMetric.objects.get(timestamp=timestamp)

        # Assert that we got back the record we saved
        assert fetched.name == "foo"
        assert fetched.value == 3.0
        assert fetched.timestamp == timestamp
        assert fetched.repo_id == 1
        assert fetched.owner_id == 2
        assert fetched.commit_id == 3
