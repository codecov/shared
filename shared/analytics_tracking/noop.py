import logging

from shared.analytics_tracking.base import BaseAnalyticsTool

log = logging.getLogger("__name__")


class NoopTool(BaseAnalyticsTool):
    @classmethod
    def is_enabled(cls):
        return False

    def track_event(self, user_id, event_name, *, is_enterprise, event_data={}):
        return
