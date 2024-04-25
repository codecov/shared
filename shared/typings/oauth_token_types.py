from typing import Any, Awaitable, Callable, Optional, TypedDict


class Token(TypedDict):
    key: str


class OauthConsumerToken(Token):
    secret: Optional[str]
    refresh_token: Optional[str]


OnRefreshCallback = Optional[Callable[[OauthConsumerToken], Awaitable[None]]]
