from unittest.mock import patch

from django.test import override_settings

from shared.django_apps.db_routers import MultiDatabaseRouter, TelemetryDatabaseRouter
from shared.django_apps.pg_telemetry.models import SimpleMetric as PgSimpleMetric
from shared.django_apps.ts_telemetry.models import SimpleMetric as TsSimpleMetric


class TestMultiDatabaseRouter:
    @override_settings(
        TIMESERIES_DATABASE_READ_REPLICA_ENABLED=True,
        DATABASE_READ_REPLICA_ENABLED=True,
    )
    def test_db_for_read_read_replica(self, mocker):
        # At time of writing, the Django timeseries models don't live in this
        # repo so we're pretending a different model is from the timeseries app
        mocker.patch.object(TsSimpleMetric._meta, "app_label", "timeseries")

        router = MultiDatabaseRouter()
        assert router.db_for_read(TsSimpleMetric) == "timeseries_read"
        assert router.db_for_read(PgSimpleMetric) == "default_read"

    @override_settings(
        TIMESERIES_DATABASE_READ_REPLICA_ENABLED=False,
        DATABASE_READ_REPLICA_ENABLED=False,
    )
    def test_db_for_read_no_read_replica(self, mocker):
        # At time of writing, the Django timeseries models don't live in this
        # repo so we're pretending a different model is from the timeseries app
        mocker.patch.object(TsSimpleMetric._meta, "app_label", "timeseries")

        router = MultiDatabaseRouter()
        assert router.db_for_read(TsSimpleMetric) == "timeseries"
        assert router.db_for_read(PgSimpleMetric) == "default"

    def test_db_for_write(self, mocker):
        # At time of writing, the Django timeseries models don't live in this
        # repo so we're pretending a different model is from the timeseries app
        mocker.patch.object(TsSimpleMetric._meta, "app_label", "timeseries")

        router = MultiDatabaseRouter()
        assert router.db_for_write(TsSimpleMetric) == "timeseries"
        assert router.db_for_write(PgSimpleMetric) == "default"

    @override_settings(TIMESERIES_ENABLED=True)
    def test_allow_migrate_timeseries_enabled(self):
        router = MultiDatabaseRouter()
        assert router.allow_migrate("timeseries", "timeseries") == True
        assert router.allow_migrate("timeseries_read", "timeseries") == False
        assert router.allow_migrate("timeseries", "default") == False
        assert router.allow_migrate("timeseries_read", "default") == False
        assert router.allow_migrate("default", "default") == True
        assert router.allow_migrate("default_read", "default") == False
        assert router.allow_migrate("default", "timeseries") == False
        assert router.allow_migrate("default_read", "timeseries") == False

    @override_settings(TIMESERIES_ENABLED=False)
    def test_allow_migrate_timeseries_disabled(self):
        router = MultiDatabaseRouter()
        assert router.allow_migrate("timeseries", "timeseries") == False
        assert router.allow_migrate("timeseries_read", "timeseries") == False
        assert router.allow_migrate("timeseries", "default") == False
        assert router.allow_migrate("timeseries_read", "default") == False
        assert router.allow_migrate("default", "default") == True
        assert router.allow_migrate("default_read", "default") == False
        assert router.allow_migrate("default", "timeseries") == False
        assert router.allow_migrate("default_read", "timeseries") == False

    def test_allow_relation(self, mocker):
        # At time of writing, the Django timeseries models don't live in this
        # repo so we're pretending a different model is from the timeseries app
        mocker.patch.object(TsSimpleMetric._meta, "app_label", "timeseries")

        router = MultiDatabaseRouter()
        assert router.allow_relation(TsSimpleMetric, TsSimpleMetric) == True
        assert router.allow_relation(PgSimpleMetric, TsSimpleMetric) == False
        assert router.allow_relation(TsSimpleMetric, PgSimpleMetric) == False
        assert router.allow_relation(PgSimpleMetric, PgSimpleMetric) == True

        # TODO the below assert should succeed but due to a pre-existing bug in
        # MultiDatabaseRouter it doesn't. Fix hte bug and uncomment
        """
        # Undo the mock so we can test with the original value
        mocker.patch.object(TsSimpleMetric._meta, 'app_label', "ts_telemetry")
        assert router.allow_relation(TsSimpleMetric, PgSimpleMetric) == False
        """


class TestTelemetryDatabaseRouter:
    @override_settings(
        TELEMETRY_VANILLA_DB="default", TELEMETRY_TIMESCALE_DB="timeseries"
    )
    def test_db_for_read(self):
        router = TelemetryDatabaseRouter()
        assert router.db_for_read(PgSimpleMetric) == "default"
        assert router.db_for_read(TsSimpleMetric) == "timeseries"

    @override_settings(
        TELEMETRY_VANILLA_DB="default", TELEMETRY_TIMESCALE_DB="timeseries"
    )
    def test_db_for_write(self):
        router = TelemetryDatabaseRouter()
        assert router.db_for_read(PgSimpleMetric) == "default"
        assert router.db_for_read(TsSimpleMetric) == "timeseries"

    @override_settings(
        TELEMETRY_VANILLA_DB="default", TELEMETRY_TIMESCALE_DB="timeseries"
    )
    def test_allow_migrate(self):
        router = TelemetryDatabaseRouter()
        assert router.allow_migrate("default", "pg_telemetry") == True
        assert router.allow_migrate("timeseries", "ts_telemetry") == True
        assert router.allow_migrate("timeseries", "pg_telemetry") == False
        assert router.allow_migrate("default", "ts_telemetry") == False
        assert router.allow_migrate("default", "timeseries") is None
        assert router.allow_migrate("timeseries", "timeseries") is None

    @override_settings(
        TELEMETRY_VANILLA_DB="default", TELEMETRY_TIMESCALE_DB="timeseries"
    )
    def test_allow_relation(self, mocker):
        router = TelemetryDatabaseRouter()
        assert router.allow_relation(TsSimpleMetric, TsSimpleMetric) == True
        assert router.allow_relation(PgSimpleMetric, TsSimpleMetric) == False
        assert router.allow_relation(TsSimpleMetric, PgSimpleMetric) == False
        assert router.allow_relation(PgSimpleMetric, PgSimpleMetric) == True

        # At time of writing, the Django timeseries models don't live in this
        # repo so we're pretending a different model is from the timeseries app
        mocker.patch.object(TsSimpleMetric._meta, "app_label", "timeseries")

        assert router.allow_relation(PgSimpleMetric, TsSimpleMetric) == False
        assert router.allow_relation(TsSimpleMetric, PgSimpleMetric) == False
        assert router.allow_relation(TsSimpleMetric, TsSimpleMetric) is None
