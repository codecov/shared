import logging

import analytics

from shared.analytics_tracking.base import BaseAnalyticsTool
from shared.analytics_tracking.events import Events
from shared.config import get_config

log = logging.getLogger("__name__")


class Segment(BaseAnalyticsTool):
    def __init__(self) -> None:
        self.setup_analytics()

    @classmethod
    def is_enabled(cls):
        return bool(get_config("setup", "segment", "enabled", default=False))

    def on_error(self, error):
        log.error("Error tracking with segment", extra=dict(error=error))

    def setup_analytics(self):
        analytics.write_key = get_config("setup", "segment", "key", default=None)
        analytics.debug = get_config("setup", "debug", default=False)
        analytics.on_error = self.on_error

    def track_event(
        self, user_id, event_name, *, is_enterprise=False, event_data={}, context=None
    ):
        """
        https://segment.com/docs/connections/spec/track/

        Track a specific event and accompanying data.
        Depending on the event, "user_id" can populated by either:

        - The ownerid of the organization associated with this event,
        when applicable. (May be the same as ownerid of logged-in user,
        if event relates to resources on their personal account rather than
        a team or organization)
        Examples: plan changed, repo activated, coverage report uploaded.

        - The ownerid of the logged-in user, when the event isn't specific
        to a particular organization or resource.
        Examples: sign in, sign out.

        For more context on how segment will store this data, see:
        https://segment.com/docs/connections/warehouses/#tracks
        https://segment.com/docs/connections/warehouses/#event-tables
        """
        if is_enterprise or not self.is_enabled():
            return

        if event_name not in list(event.value for event in Events):
            log.debug("Invalid event name: " + event_name)
            return
        try:
            analytics.track(user_id, event_name, event_data, context)
        except Exception:
            log.exception("Unable to track event", extra=dict(event_name=event_name))

    def track_user(self, user_id, user_data={}, is_enterprise=False):
        """
        https://segment.com/docs/connections/spec/identify/
        Save information associated with a specific user, where "user"
        corresponds to our "Owner" data model and can therefore be either a user
        or an organization.
        For more context on how segment will store this data, see:
        https://segment.com/docs/connections/warehouses/#identifies
        """
        if is_enterprise or not self.is_enabled():
            return

        analytics.identify(user_id, user_data)
