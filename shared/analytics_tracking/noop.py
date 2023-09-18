import logging

from shared.analytics_tracking.base import BaseAnalyticsTool
from shared.analytics_tracking.events import Event

log = logging.getLogger("__name__")


class NoopTool(BaseAnalyticsTool):
    @classmethod
    def is_enabled(cls):
        return False

    def track_event(self, event: Event, *, is_enterprise, context: None):
        return
