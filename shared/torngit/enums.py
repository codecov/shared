from enum import Enum, auto
from typing import Callable, Coroutine, Optional, TypedDict


class Endpoints(Enum):
    commit_detail = auto()


class OauthConsumerToken(TypedDict):
    key: str
    secret: str
    refresh_token: str
    redirect_uri_no_protocol: Optional[str]


OnRefreshCallback = Optional[Callable[[OauthConsumerToken], None]]
