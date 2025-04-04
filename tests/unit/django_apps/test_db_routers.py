from django.test import override_settings

from shared.django_apps.codecov_auth.models import Owner
from shared.django_apps.db_routers import MultiDatabaseRouter


class TestMultiDatabaseRouter:
    @override_settings(
        TIMESERIES_DATABASE_READ_REPLICA_ENABLED=True,
        DATABASE_READ_REPLICA_ENABLED=True,
    )
    def test_db_for_read_read_replica(self, mocker):
        # At time of writing, the Django timeseries models don't live in this
        # repo so we're pretending a different model is from the timeseries app
        mocker.patch.object(Owner._meta, "app_label", "timeseries")

        router = MultiDatabaseRouter()
        assert router.db_for_read(Owner) == "timeseries_read"

    @override_settings(
        TIMESERIES_DATABASE_READ_REPLICA_ENABLED=False,
        DATABASE_READ_REPLICA_ENABLED=False,
    )
    def test_db_for_read_no_read_replica(self, mocker):
        # At time of writing, the Django timeseries models don't live in this
        # repo so we're pretending a different model is from the timeseries app
        mocker.patch.object(Owner._meta, "app_label", "timeseries")

        router = MultiDatabaseRouter()
        assert router.db_for_read(Owner) == "timeseries"

    def test_db_for_write(self, mocker):
        # At time of writing, the Django timeseries models don't live in this
        # repo so we're pretending a different model is from the timeseries app
        mocker.patch.object(Owner._meta, "app_label", "timeseries")

        router = MultiDatabaseRouter()
        assert router.db_for_write(Owner) == "timeseries"

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
        mocker.patch.object(Owner._meta, "app_label", "timeseries")

        router = MultiDatabaseRouter()
        assert router.allow_relation(Owner, Owner) == True
