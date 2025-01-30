import logging
from typing import Literal, TypedDict, Union

from amplitude import Amplitude, BaseEvent, Config, EventOptions
from django.conf import settings

from shared.events.base import EventPublisher, MissingEventPropertyException
from shared.utils.snake_to_camel_case import snake_to_camel_case

log = logging.getLogger(__name__)

"""

Add new events as a string in the AmplitudeEventType type below!

Adding event types in this way provides type safety for names and allows us to
specify required properties.
E.g., every 'App Installed' event must have the 'ownerid' property.

Guidelines:
 - Event names should:
   - be of the form "[Noun] [Past-tense verb]",
   - have each word capitalized,
   - describe an action taken by the user.
 - Keep the event types very generic as we have a limited number of them.
   Instead, add more detail in `properties` where possible.
 - Try to keep event property names unique to the event type to avoid
   accidental correlation of unrelated events.
 - Never include names, only use ids. E.g., use repoid instead of repo name.

"""

type AmplitudeEventType = Literal[
    "User Created",
    "App Installed",
    "Upload Sent",
    "set_orgs",  # special event for setting a user's member orgs
]

"""

Add Event Properties here, define their types in AmplitudeEventProperties,
and finally add them as required properties where needed in
amplitude_required_properties.

Note: these are converted to camel case before they're sent to Amplitude!

"""
type AmplitudeEventProperty = Literal[
    "user_ownerid",
    "ownerid",
    "org_ids",
    "repoid",
    "upload_type",
]


# Separate type required to make user_ownerid mandatory with total=True
class BaseAmplitudeEventProperties(TypedDict, total=True):
    user_ownerid: int  # ownerid of user performing event action


class AmplitudeEventProperties(BaseAmplitudeEventProperties, total=False):
    ownerid: int  # ownerid of owner being acted upon
    org_ids: list[int]
    repoid: int
    upload_type: Literal["Coverage report", "Bundle", "Test results"]


# user_ownerid is always required, don't need to check here.
amplitude_required_properties: dict[
    AmplitudeEventType, list[AmplitudeEventProperty]
] = {
    "User Created": [],
    "App Installed": ["ownerid"],
    "Upload Sent": ["ownerid", "repoid", "upload_type"],
}


class AmplitudeEventPublisher(EventPublisher):
    """

    EventPublisher for Amplitude events.

    """

    client: Amplitude

    def __init__(self):
        api_key = settings.AMPLITUDE_API_KEY
        if api_key is None:
            log.warning(
                "AMPLITUDE_API_KEY is not defined. Amplitude events will not be tracked."
            )
            self.client = StubbedAmplitudeClient()
        else:
            # min_id_length necessary to accommodate our ownerids
            self.client = Amplitude(api_key, Config(min_id_length=1))

    def publish(
        self, event_type: AmplitudeEventType, event_properties: AmplitudeEventProperties
    ):
        # Handle special set_orgs event
        if event_type == "set_orgs":
            if "org_ids" not in event_properties:
                raise MissingEventPropertyException(
                    "Property 'org_ids' is required for event type 'set_orgs'"
                )

            self.client.set_group(
                group_type="org",
                group_name=[str(orgid) for orgid in event_properties["org_ids"]],
                event_options=EventOptions(
                    user_id=str(event_properties["user_ownerid"])
                ),
            )
            return

        # Handle normal events
        structured_payload = transform_properties(event_type, event_properties)

        # Track event with validated payload, we will raise an exception before
        # this if bad payload.
        self.client.track(
            BaseEvent(
                event_type,
                user_id=str(event_properties["user_ownerid"]),
                event_properties=structured_payload,
            )
        )
        return


class StubbedAmplitudeClient(Amplitude):
    """

    Stubbed Amplitude client for use when no AMPLITUDE_API_KEY is defined.

    """

    def __init__(self):
        return

    def set_group(
        self,
        group_type: str,
        group_name: Union[str, list[str]],
        event_options: EventOptions,
    ):
        return

    def track(self, event: BaseEvent):
        return


def transform_properties(
    event_type: AmplitudeEventType, event_properties: AmplitudeEventProperties
) -> dict:
    """

    Helper function to validate all required properties exist for the provided
    event_type and ensure only those properties are sent in the payload.

    """

    payload = {}

    for property in amplitude_required_properties[event_type]:
        if property not in event_properties:
            raise MissingEventPropertyException(
                f"Property {property} is required for event type {event_type}"
            )
        payload[snake_to_camel_case(property)] = event_properties.get(property)

    return payload
