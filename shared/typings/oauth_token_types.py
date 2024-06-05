from typing import Awaitable, Callable, Optional, TypedDict


class Token(TypedDict):
    key: str
    # This information is used to identify the token owner in the logs, if present
    username: str | None


class OauthConsumerToken(Token):
    secret: Optional[str]
    refresh_token: Optional[str]


OnRefreshCallback = Optional[Callable[[OauthConsumerToken], Awaitable[None]]]
