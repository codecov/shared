from typing import Awaitable, Callable, Optional, TypedDict


class Token(TypedDict):
    key: str
    # This information is used to identify the token owner in the logs, if present
    username: str | None
    # This represents the entity it belongs to. Entities can have the form of
    # <app_id>_<installation_id> for Github Apps
    # <owner_id> for Owners
    # <TokenType> for mapped Tokens if available
    # github_bot for Anonymous users
    entity_name: str | None


class OauthConsumerToken(Token):
    secret: Optional[str]
    refresh_token: Optional[str]


OnRefreshCallback = Optional[Callable[[OauthConsumerToken], Awaitable[None]]]
