import logging

from django.conf import settings

log = logging.getLogger(__name__)


class MultiDatabaseRouter:
    """
    A router to control all database operations on models across multiple databases.
    https://docs.djangoproject.com/en/4.0/topics/db/multi-db/#automatic-database-routing
    """

    def db_for_read(self, model, **hints):
        match model._meta.app_label:
            case "timeseries":
                if settings.TIMESERIES_DATABASE_READ_REPLICA_ENABLED:
                    return "timeseries_read"
                else:
                    return "timeseries"
            case "test_analytics":
                return "test_analytics"
            case _:
                if settings.DATABASE_READ_REPLICA_ENABLED:
                    return "default_read"
                else:
                    return "default"

    def db_for_write(self, model, **hints):
        match model._meta.app_label:
            case "timeseries":
                return "timeseries"
            case "test_analytics":
                return "test_analytics"
            case _:
                return "default"

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        match db:
            case "timeseries_read" | "test_analytics_read" | "default_read":
                log.warning("Skipping migration of read-only database")
                return False
            case "timeseries":
                if not settings.TIMESERIES_ENABLED:
                    log.warning("Skipping migration of timeseries")
                    return False
                return app_label == "timeseries"
            case "test_analytics":
                if not settings.TEST_ANALYTICS_DATABASE_ENABLED:
                    log.warning("Skipping migration of test_analytics")
                    return False
                return app_label == "test_analytics"
            case _:
                return app_label not in {"timeseries", "test_analytics"}

    def allow_relation(self, obj1, obj2, **hints):
        obj1_app = obj1._meta.app_label
        obj2_app = obj2._meta.app_label

        if obj1_app in {"timeseries", "test_analytics"} or obj2_app in {
            "timeseries",
            "test_analytics",
        }:
            return obj1_app == obj2_app
        else:
            return True
