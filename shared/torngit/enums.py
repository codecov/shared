from enum import Enum, auto
from typing import Callable, Optional
from mypy_extensions import TypedDict


class Endpoints(Enum):
    commit_detail = auto()


class OauthConsumerToken(TypedDict):
    key: str
    secret: str
    refresh_token: str
    redirect_uri_no_protocol: Optional[str]


OnRefreshCallback = Optional[Callable[[OauthConsumerToken], None]]
