from typing import Any, Awaitable, Callable, Optional, TypedDict


class Token(TypedDict):
    key: str
    # The installation ID that this token belongs to
    # Used to mark them as rate-limited
    installation_id: Optional[int] = None


class OauthConsumerToken(Token):
    secret: Optional[str]
    refresh_token: Optional[str]


OnRefreshCallback = Optional[Callable[[OauthConsumerToken], Awaitable[None]]]
