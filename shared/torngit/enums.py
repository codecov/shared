from dataclasses import dataclass
from enum import Enum, auto
from typing import Callable, Optional


class Endpoints(Enum):
    commit_detail = auto()


@dataclass
class OauthConsumerToken:
    key: str
    secret: str
    refresh_token: str


OnRefreshCallback = Optional[Callable[[OauthConsumerToken], None]]
