from dataclasses import dataclass
from typing import Callable, Optional


@dataclass
class OauthConsumerToken(object):
    key: str
    secret: str
    refresh_token: str


OnRefreshCallback = Optional[Callable[[OauthConsumerToken], None]]
