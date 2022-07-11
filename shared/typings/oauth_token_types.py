from typing import Any, Awaitable, Callable, Optional

# FIXME: This is actually a TypedDict
# But our CircleCI currently doesn't support Python 3.8, needed for TypedDicts
# So this will seat here until we update it
# OauthConsumerToken(TypedDict):
#   key: str
#   secret: str
#   refresh_token: str
OauthConsumerToken = Any

OnRefreshCallback = Optional[Callable[[OauthConsumerToken], Awaitable[None]]]
