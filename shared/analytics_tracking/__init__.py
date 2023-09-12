import logging
from typing import List

from shared.analytics_tracking.base import BaseAnalyticsTool
from shared.analytics_tracking.manager import AnalyticsToolManager
from shared.analytics_tracking.noop import NoopTool
from shared.analytics_tracking.pubsub import PubSub
from shared.analytics_tracking.segment import Segment

log = logging.getLogger("__name__")

__all__ = "analytics_tool"


def get_list_of_analytic_tools() -> List[BaseAnalyticsTool]:
    return [Segment(), PubSub()]


def get_tools_manager():
    tool_manager = AnalyticsToolManager()
    available_tools = get_list_of_analytic_tools()
    for tool in available_tools:
        tool_manager.add_tool(tool)

    # Noop shouldn't be added unless there are no tracking tools used
    if not available_tools:
        log.warning("Analytics tool is not enabled. Please check your configuration.")
        tool_manager.add_tool(NoopTool)
    return tool_manager


analytics_tool = get_tools_manager()
