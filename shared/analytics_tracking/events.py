import logging
from base64 import b64encode
from datetime import datetime
from enum import Enum
from typing import Any, Mapping
from uuid import uuid1

import pytz

from shared.helpers.date import to_timestamp

log = logging.getLogger("__name__")


class Events(Enum):
    ACCOUNT_ACTIVATED_REPOSITORY_ON_UPLOAD = "Account Activated Repository On Upload"
    ACCOUNT_ACTIVATED_REPOSITORY = "Account Activated Repository"
    ACCOUNT_UPLOADED_COVERAGE_REPORT = "Account Uploaded Coverage Report"
    USER_SIGNED_IN = "User Signed In"
    USER_SIGNED_UP = "User Signed Up"


class Event:
    def __init__(self, event_name: str, dt: datetime = None, **data: Any) -> None:
        self.uuid = uuid1()
        self.datetime = dt or datetime.now(tz=pytz.utc)
        self.name = self._get_event_name(event_name)
        self.data = data

    def _get_event_name(self, event_name: str):
        if event_name not in list(event.value for event in Events):
            raise ValueError("Invalid event name: " + event_name)
        return event_name

    def serialize(self) -> Mapping[str, Any]:
        return {
            "uuid": b64encode(self.uuid.bytes).decode(),
            "timestamp": to_timestamp(self.datetime),
            "type": self.name,
            "data": self.data,
        }
