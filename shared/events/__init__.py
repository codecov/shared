from abc import ABC, abstractmethod
from typing import Literal, Optional
from amplitude import Amplitude, BaseEvent, Config, EventOptions

AMPLITUDE_API_KEY = None

__all__ = [
    "Event",
    "event_tracker",
]

type EventType = Literal[
    "Owner Created", # User owner, not org owner.
    "App Installed",
    "Coverage Uploaded"
]

class Event():
    type: EventType
    properties: Optional[dict]

    def __init__(self, event_type: EventType, properties: Optional[dict] = None):
        # Enforce event property constraints at runtime.
        if event_type == 'Owner Created':
            assert properties is None

        if event_type == "Coverage Uploaded":
            assert properties is not None
            assert type(properties.get('ci', None)) == 'str'

        self.type = event_type
        self.properties = properties

class EventTracker(ABC):
    """
    Tracks an event performed by ownerid.
    """
    @abstractmethod
    def track(self, ownerid: int, event: Event):
        pass

    """
    Updates org memberships for user with ownerid.
    """
    @abstractmethod
    def set_orgs(self, ownerid: int, org_ids: list[int]):
        pass


class StubbedEventTracker(EventTracker):
    def track(self, ownerid: int, event: Event):
        pass

    def set_orgs(self, ownerid: int, org_ids: list[int]):
        pass

class AmplitudeEventTracker(EventTracker):
    client: Amplitude

    def __init__(self):
        if AMPLITUDE_API_KEY is None:
            raise Exception("AMPLITUDE_API_KEY is not defined. Amplitude events will not be tracked.")
        
        self.client = Amplitude(AMPLITUDE_API_KEY, Config(
            min_id_length=1  # necessary to accommodate our ownerids
        ))

    def track(self, ownerid: int, event: Event):
        self.client.track(
            BaseEvent(event.type, user_id=str(ownerid), event_properties=event.properties)
        )

    def set_orgs(self, ownerid: int, org_ids: list[int]):
        self.client.set_group(
            group_type="org", 
            group_name=[str(orgid) for orgid in org_ids], 
            event_options=EventOptions(user_id=str(ownerid))
        )

EVENT_TRACKER = StubbedEventTracker()

"""Returns active EventTracker singleton."""
def event_tracker() -> EventTracker:
    global EVENT_TRACKER
    if isinstance(EVENT_TRACKER, StubbedEventTracker):
        try:
            EVENT_TRACKER = AmplitudeEventTracker()
        except:
            pass
    return EVENT_TRACKER

