from typing import Any, Awaitable, Callable, Optional, TypedDict


class OauthConsumerToken(TypedDict):
    key: str
    secret: str
    refresh_token: str


OnRefreshCallback = Optional[Callable[[OauthConsumerToken], Awaitable[None]]]
