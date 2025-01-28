from typing import Literal, TypedDict
from shared.events.base import EventPublisher, EventPublisherPropertyException
from amplitude import Amplitude, BaseEvent, Config, EventOptions

AMPLITUDE_API_KEY = None

type AmplitudeEventType = Literal[
    "User Created",
    "App Installed",
    "Coverage Uploaded",
    "set_orgs" # special event for setting a user's member orgs
]

type AmplitudeEventProperty = Literal[
    "user_ownerid",
    "ownerid",
    "org_ids",
]

# Separate type required to make user_ownerid mandatory, but all others optional
class BaseAmplitudeEventProperties(TypedDict, total=True):
    user_ownerid: int # ownerid of user performing event action

class AmplitudeEventProperties(BaseAmplitudeEventProperties, total=False):
    ownerid: int # ownerid of owner being acted upon
    org_ids: list[str]

# user_ownerid is always required, don't need to check here.
amplitude_required_properties: dict[AmplitudeEventType, list[AmplitudeEventProperty]] = {
    'App Installed': ['ownerid']
}

class AmplitudeEventPublisher(EventPublisher):
    client: Amplitude

    def __init__(self):
        if AMPLITUDE_API_KEY is None:
            raise Exception("AMPLITUDE_API_KEY is not defined. Amplitude events will not be tracked.")
        
        self.client = Amplitude(AMPLITUDE_API_KEY, Config(
            min_id_length=1  # necessary to accommodate our ownerids
        ))

    def publish(self, event_type: AmplitudeEventType, event_properties: AmplitudeEventProperties):
        # Handle special set_orgs event
        if event_type == "set_orgs":
            if 'org_ids' not in event_properties:
                raise EventPublisherPropertyException("event_type 'set_orgs' requires property 'org_ids'")

            self.client.set_group(
                group_type="org", 
                group_name=[str(orgid) for orgid in event_properties['org_ids']], 
                event_options=EventOptions(user_id=str(event_properties['user_ownerid']))
            )
            return

        # Handle normal events
        structured_payload = transform_properties(event_type, event_properties)

        # Track event with validated payload, we will raise an exception before
        # this if bad payload.
        self.client.track(
            BaseEvent(event_type, user_id=str(event_properties['user_ownerid']), event_properties=structured_payload)
        )
        return

def transform_properties(event_type: AmplitudeEventType, event_properties: AmplitudeEventProperties) -> dict:
    payload = {}

    for property in amplitude_required_properties[event_type]:
        if property not in event_properties:
            raise EventPublisherPropertyException(f"Property {property} is required for event type {event_type}")
        payload[property] = event_properties.get(property)

    return payload

