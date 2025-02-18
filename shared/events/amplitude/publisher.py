import logging
from typing import Union

from django.conf import settings

from amplitude import Amplitude, BaseEvent, Config, EventOptions
from shared.environment.environment import get_current_env, Environment
from shared.events.amplitude.types import (
    AMPLITUDE_REQUIRED_PROPERTIES,
    AmplitudeEventProperties,
    AmplitudeEventType,
)
from shared.events.base import (
    EventPublisher,
    MissingEventPropertyException,
)
from shared.utils.snake_to_camel_case import snake_to_camel_case

log = logging.getLogger(__name__)


class AmplitudeEventPublisher(EventPublisher):
    """

    EventPublisher for Amplitude events.

    """

    client: Amplitude

    def __init__(self, override_env=False):
        if get_current_env() != Environment.production and not override_env:
            log.info("RUN_ENV is not production. Amplitude events will not be tracked.")
            self.client = StubbedAmplitudeClient()
            return

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
        structured_payload = self.__transform_properties(event_type, event_properties)

        # Track event with validated payload, we will raise an exception before
        # this if bad payload.
        org = structured_payload.get("ownerid", None)
        self.client.track(
            BaseEvent(
                event_type,
                user_id=str(event_properties["user_ownerid"]),
                event_properties=structured_payload,
                groups={"org": org} if org is not None else {},
            )
        )
        return

    def __transform_properties(
        self, event_type: AmplitudeEventType, event_properties: AmplitudeEventProperties
    ) -> dict:
        """

        Helper function to validate all required properties exist for the provided
        event_type and ensure only those properties are sent in the payload.

        """

        payload = {}

        for property in AMPLITUDE_REQUIRED_PROPERTIES[event_type]:
            if property not in event_properties:
                raise MissingEventPropertyException(
                    f"Property {property} is required for event type {event_type}"
                )

            payload[snake_to_camel_case(property)] = event_properties.get(property)

        return payload


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
        log.info(f'StubbedAmplitudeClient set_group {group_type}: {group_name}', extra=event_options.get_event_body())
        return

    def track(self, event: BaseEvent):
        log.info(f'StubbedAmplitudeClient tracked event {event.event_type}', extra=event.get_event_body())
        return
