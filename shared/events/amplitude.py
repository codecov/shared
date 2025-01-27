from typing import Literal, TypedDict
from shared.events.base import EventPublisher, EventPublisherPropertyError
from amplitude import Amplitude, BaseEvent, Config, EventOptions

AMPLITUDE_API_KEY = None

type AmplitudeEventType = Literal[
    "User Created",
    "App Installed",
    "Coverage Uploaded",
    "set_orgs" # special event for setting a user's member orgs
]

# Separate type required to make user_owner_id mandatory, but all others optional
class BaseAmplitudeEventProperties(TypedDict, total=True):
    user_owner_id: int # ownerid of user performing event action

class AmplitudeEventProperties(BaseAmplitudeEventProperties, total=False):
    ownerid: int # ownerid of owner being acted upon
    org_ids: list[str]

class AmplitudeEventPublisher(EventPublisher):
    client: Amplitude

    def __init__(self):
        if AMPLITUDE_API_KEY is None:
            raise Exception("AMPLITUDE_API_KEY is not defined. Amplitude events will not be tracked.")
        
        self.client = Amplitude(AMPLITUDE_API_KEY, Config(
            min_id_length=1  # necessary to accommodate our ownerids
        ))

    def publish(self, event_type: AmplitudeEventType, event_properties: AmplitudeEventProperties):
        if event_type == "set_orgs":
            if 'org_ids' not in event_properties:
                raise EventPublisherPropertyError("event_type 'set_orgs' requires property 'org_ids'")

            self.client.set_group(
                group_type="org", 
                group_name=[str(orgid) for orgid in event_properties['org_ids']], 
                event_options=EventOptions(user_id=str(event_properties['user_owner_id']))
            )


        self.client.track(
            BaseEvent(event_type, user_id=str(event_properties['user_owner_id']), event_properties=dict(event_properties))
        )

a = AmplitudeEventPublisher()

a.publish('set_orgs', {"user_owner_id": 2, "org_ids": ['1', '2']})
