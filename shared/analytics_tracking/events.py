import logging
from base64 import b64encode
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Mapping
from uuid import uuid1

log = logging.getLogger("__name__")


class Events(Enum):
    ACCOUNT_ACTIVATED_REPOSITORY_ON_UPLOAD = (
        "codecov.account.activated_repository_on_upload"
    )
    ACCOUNT_ACTIVATED_REPOSITORY = "codecov.account.activated_repository"
    ACCOUNT_UPLOADED_COVERAGE_REPORT = "codecov.account.uploaded_coverage_report"
    USER_SIGNED_IN = "codecov.user.signed_in"
    USER_SIGNED_UP = "codecov.user.signed_up"
    GDPR_OPT_IN = "codecov.email.gdpr_opt_in"


class Event:
    def __init__(self, event_name: str, dt: datetime | None = None, **data) -> None:
        self.uuid = uuid1()
        self.datetime = dt or datetime.now(timezone.utc)
        self.name = self._get_event_name(event_name)
        self.data = data

    def _get_event_name(self, event_name: str):
        if event_name not in list(event.value for event in Events):
            raise ValueError("Invalid event name: " + event_name)
        return event_name

    def serialize(self) -> Mapping[str, Any]:
        return {
            "uuid": b64encode(self.uuid.bytes).decode(),
            "timestamp": self.datetime.timestamp(),
            "type": self.name,
            "data": self.data,
        }
