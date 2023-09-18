from abc import ABC, abstractmethod

from shared.analytics_tracking.events import Event


class BaseAnalyticsTool(ABC):
    BLANK_USER_ID = -1

    @classmethod
    @abstractmethod
    def is_enabled(cls):
        raise NotImplementedError()

    def track_event(self, event: Event, *, is_enterprise, context: None):
        raise NotImplementedError()
