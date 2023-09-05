from abc import ABC, abstractmethod


class BaseAnalyticsTool(ABC):
    BLANK_USER_ID = -1

    @classmethod
    @abstractmethod
    def is_enabled(cls):
        raise NotImplementedError()

    def track_event(self, user_id, event_name, *, is_enterprise, event_data={}):
        raise NotImplementedError()

    def track_user(self, user_id, user_data={}, is_enterprise=False):
        raise NotImplementedError()
