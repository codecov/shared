import logging

from django.conf import settings

log = logging.getLogger(__name__)


class MultiDatabaseRouter:
    """
    A router to control all database operations on models across multiple databases.
    https://docs.djangoproject.com/en/4.0/topics/db/multi-db/#automatic-database-routing
    """

    def db_for_read(self, model, **hints):
        if model._meta.app_label == "timeseries":
            if settings.TIMESERIES_DATABASE_READ_REPLICA_ENABLED:
                return "timeseries_read"
            else:
                return "timeseries"
        else:
            if settings.DATABASE_READ_REPLICA_ENABLED:
                return "default_read"
            else:
                return "default"

    def db_for_write(self, model, **hints):
        if model._meta.app_label == "timeseries":
            return "timeseries"
        else:
            return "default"

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if (
            db == "timeseries" or db == "timeseries_read"
        ) and not settings.TIMESERIES_ENABLED:
            log.warning("Skipping timeseries migration")
            return False
        if db == "default_read" or db == "timeseries_read":
            log.warning("Skipping migration of read-only database")
            return False
        if app_label == "timeseries":
            return db == "timeseries"
        else:
            return db == "default"

    def allow_relation(self, obj1, obj2, **hints):
        obj1_app = obj1._meta.app_label
        obj2_app = obj2._meta.app_label

        # cannot form relationship across default <-> timeseries dbs
        if obj1_app == "timeseries" and obj2_app != "timeseries":
            return False
        if obj1_app != "timeseries" and obj2_app == "timeseries":
            return False

        # otherwise we allow it
        return True


class TelemetryDatabaseRouter:
    """
    We are evaluating whether we still want to run a TimescaleDB instance for
    our telemetry or whether our normal database (PostgreSQL/AlloyDB) does the
    trick. After data is flowing through both for a time, we'll pick one.
    """

    def db_for_read(self, model, **hints):
        if model._meta.app_label == "pg_telemetry":
            return settings.TELEMETRY_VANILLA_DB
        elif model._meta.app_label == "ts_telemetry":
            return settings.TELEMETRY_TIMESCALE_DB

        return None

    def db_for_write(self, model, **hints):
        if model._meta.app_label == "pg_telemetry":
            return settings.TELEMETRY_VANILLA_DB
        elif model._meta.app_label == "ts_telemetry":
            return settings.TELEMETRY_TIMESCALE_DB

        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if app_label == "pg_telemetry":
            return db == settings.TELEMETRY_VANILLA_DB
        elif app_label == "ts_telemetry":
            return db == settings.TELEMETRY_TIMESCALE_DB

        return None

    def allow_relation(self, l, r, **hints):
        if l._meta.app_label in (
            "pg_telemetry",
            "ts_telemetry",
        ) or r._meta.app_label in (
            "pg_telemetry",
            "ts_telemetry",
        ):
            return l._meta.app_label == r._meta.app_label

        return None
