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

from typing import Literal, TypedDict

type AmplitudeEventType = Literal[
    "User Created",
    "User Logged in",
    "App Installed",
    "Upload Sent",
    "set_orgs",  # special event for setting a user's member orgs
]

"""

Add Event Properties here, define their types in AmplitudeEventProperties,
and finally add them as required properties where needed in
AMPLITUDE_REQUIRED_PROPERTIES.

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
AMPLITUDE_REQUIRED_PROPERTIES: dict[
    AmplitudeEventType, list[AmplitudeEventProperty]
] = {
    "User Created": [],
    "User Logged in": [],
    "App Installed": ["ownerid"],
    "Upload Sent": ["ownerid", "repoid", "upload_type"],
}
