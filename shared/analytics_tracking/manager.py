import logging
from typing import Optional

from shared.analytics_tracking.base import BaseAnalyticsTool
from shared.analytics_tracking.events import Event

log = logging.getLogger("__name__")


class AnalyticsToolManager:
    def __init__(self):
        self.tools = []

    def add_tool(self, tracking_tool: BaseAnalyticsTool):
        self.tools.append(tracking_tool)

    def remove_tool(self, tracking_tool: BaseAnalyticsTool):
        self.tools.remove(tracking_tool)

    def track_event(
        self,
        event_name,
        *,
        is_enterprise=False,
        event_data: Optional[dict] = None,
        context=None,
    ):
        if event_data is None:
            event_data = {}

        event = Event(event_name, **event_data)
        for tool in self.tools:
            if tool.is_enabled():
                try:
                    tool.track_event(
                        event, is_enterprise=is_enterprise, context=context
                    )
                except Exception as exc:
                    log.error(
                        "Got an error sending events", extra=dict(tool=tool, error=exc)
                    )
