from typing import Optional

from shared.analytics_tracking.base import BaseAnalyticsTool
from shared.analytics_tracking.events import Event


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
        context=None
    ):
        if event_data is None:
            event_data = {}

        event = Event(event_name, **event_data)
        for tool in self.tools:
            if tool.is_enabled():
                tool.track_event(event, is_enterprise=is_enterprise, context=context)
