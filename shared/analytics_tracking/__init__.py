import analytics
import logging
from schema import Schema, Or

from shared.config import get_config

log = logging.getLogger("__name__")


# Set up
def on_error(error):
    log.error("Error tracking with segment", extra=dict(error=error))


def setup_analytics():
    analytics.write_key = get_config("setup", "segment", "key", default=None)
    analytics.debug = get_config("setup", "debug", default=False)
    analytics.on_error = on_error


segment_enabled = bool(get_config("setup", "segment", "enabled", default=False))
if segment_enabled:
    setup_analytics()

event_names = [
    "Coverage Report Passed",
    "Coverage Report Failed",
]
event_name_validator = Schema(Or(*event_names))


def track_event(user_id, event_name, event_data={}, is_enterprise=False):
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
    if is_enterprise or not segment_enabled:
        return

    if not event_name_validator.is_valid(event_name):
        log.debug("Invalid event name: " + event_name)
        return

    analytics.track(user_id, event_name, event_data)


def track_user(user_id, user_data={}, is_enterprise=False):
    """
    https://segment.com/docs/connections/spec/identify/

    Save information associated with a specific user, where "user"
    corresponds to our "Owner" data model and can therefore be either a user
    or an organization.

    For more context on how segment will store this data, see:
    https://segment.com/docs/connections/warehouses/#identifies
    """
    if is_enterprise or not segment_enabled:
        return

    analytics.identify(user_id, user_data)
