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
            case "ta_timeseries":
                return "ta_timeseries"
            case _:
                if settings.DATABASE_READ_REPLICA_ENABLED:
                    return "default_read"
                else:
                    return "default"

    def db_for_write(self, model, **hints):
        match model._meta.app_label:
            case "timeseries":
                return "timeseries"
            case "ta_timeseries":
                return "ta_timeseries"
            case _:
                return "default"

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        match db:
            case "timeseries_read" | "default_read":
                return False
            case "timeseries":
                if not settings.TIMESERIES_ENABLED:
                    return False
                return app_label == "timeseries"
            case "ta_timeseries":
                if not settings.TA_TIMESERIES_ENABLED:
                    return False
                return app_label == "ta_timeseries"
            case _:
                return app_label not in {"timeseries", "ta_timeseries"}

    def allow_relation(self, obj1, obj2, **hints):
        obj1_app = obj1._meta.app_label
        obj2_app = obj2._meta.app_label

        if obj1_app in {"timeseries", "ta_timeseries"} or obj2_app in {
            "timeseries",
            "ta_timeseries",
        }:
            return obj1_app == obj2_app
        else:
            return True
