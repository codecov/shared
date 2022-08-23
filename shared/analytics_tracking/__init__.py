import logging

import analytics

from shared.config import get_config

log = logging.getLogger("__name__")

BLANK_SEGMENT_USER_ID = -1

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
    "Impact Analysis Related Entrypoints Sent",
    "Impact Analysis Critical Files Sent",
    "Impact Analysis Betaprofiling in YAML",
    "Impact Analysis Betaprofiling removed from YAML",
    "Impact Analysis Show Critical Files in YAML",
    "Impact Analysis Show Critical Files removed from YAML",
]


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

    if event_name not in event_names:
        log.debug("Invalid event name: " + event_name)
        return
    try:
        analytics.track(user_id, event_name, event_data)
    except Exception:
        log.exception("Unable to track event", extra=dict(event_name=event_name))


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


def track_critical_files_sent(repoid, ownerid, commitid, pullid, is_enterprise):
    track_event(
        user_id=BLANK_SEGMENT_USER_ID,
        event_name="Impact Analysis Critical Files Sent",
        event_data={
            "repo_id": repoid,
            "repo_owner_id": ownerid,
            "commit_id": commitid,
            "pull_id": pullid,
        },
        is_enterprise=is_enterprise,
    )


def track_betaprofiling_added_in_YAML(repoid, ownerid, is_enterprise):
    track_event(
        user_id=BLANK_SEGMENT_USER_ID,
        event_name="Impact Analysis Betaprofiling in YAML",
        event_data={"repo_id": repoid, "repo_owner_id": ownerid},
        is_enterprise=is_enterprise,
    )


def track_related_entrypoints_sent(repoid, ownerid, commitid, pullid, is_enterprise):
    track_event(
        user_id=BLANK_SEGMENT_USER_ID,
        event_name="Impact Analysis Related Entrypoints Sent",
        event_data={
            "repo_id": repoid,
            "repo_owner_id": ownerid,
            "commit_id": commitid,
            "pull_id": pullid,
        },
        is_enterprise=is_enterprise,
    )


def track_betaprofiling_removed_from_YAML(repoid, ownerid, is_enterprise):
    track_event(
        user_id=BLANK_SEGMENT_USER_ID,
        event_name="Impact Analysis Betaprofiling removed from YAML",
        event_data={"repo_id": repoid, "repo_owner_id": ownerid},
        is_enterprise=is_enterprise,
    )


def track_show_critical_paths_added_in_YAML(repoid, ownerid, is_enterprise):
    track_event(
        user_id=BLANK_SEGMENT_USER_ID,
        event_name="Impact Analysis Show Critical Files in YAML",
        event_data={"repo_id": repoid, "repo_owner_id": ownerid},
        is_enterprise=is_enterprise,
    )


def track_show_critical_paths_removed_from_YAML(repoid, ownerid, is_enterprise):
    track_event(
        user_id=BLANK_SEGMENT_USER_ID,
        event_name="Impact Analysis Show Critical Files removed from YAML",
        event_data={"repo_id": repoid, "repo_owner_id": ownerid},
        is_enterprise=is_enterprise,
    )
