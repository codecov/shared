from typing import Any, Awaitable, Callable, Optional, TypedDict


class GithubInstallationInfo(TypedDict):
    """Required info to get a token from Github for a given installation"""

    installation_id: int
    # The default app (configured via yaml) doesn't need this info.
    # All other apps need app_id and pem_path
    app_id: Optional[int] = None
    pem_path: Optional[str] = None


class Token(TypedDict):
    key: str
    # The installation ID that this token belongs to
    # Used to mark them as rate-limited
    installation_id: Optional[int] = None


class OauthConsumerToken(Token):
    secret: Optional[str]
    refresh_token: Optional[str]


OnRefreshCallback = Optional[Callable[[OauthConsumerToken], Awaitable[None]]]
