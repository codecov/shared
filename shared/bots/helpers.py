import logging
from typing import Any, Dict, Optional

from shared.bots.exceptions import RepositoryWithoutValidBotError
from shared.config import get_config
from shared.github import InvalidInstallationError
from shared.github import get_github_integration_token as _get_github_integration_token
from shared.helpers.cache import OurOwnCache, RedisBackend
from shared.helpers.redis import get_redis_connection
from shared.torngit.base import TokenType
from shared.typings.oauth_token_types import Token

cache = OurOwnCache()
cache.configure(RedisBackend(get_redis_connection()), app="shared.installation_tokens")

log = logging.getLogger(__name__)


# The integration tokens are valid for 1h
# We use 30min of that
@cache.cache_function(ttl=1800)
def get_github_integration_token(
    service: str,
    installation_id: int = None,
    app_id: Optional[str] = None,
    pem_path: Optional[str] = None,
):
    try:
        return _get_github_integration_token(
            service, integration_id=installation_id, app_id=app_id, pem_path=pem_path
        )
    except InvalidInstallationError:
        log.warning("Failed to get installation token")
        raise RepositoryWithoutValidBotError()


def get_dedicated_app_token_from_config(
    service: str, token_type: TokenType
) -> Token | None:
    # GitHub can have 'dedicated_apps', and those are preferred
    dedicated_app: Dict[str, Any] = get_config(
        service, "dedicated_apps", token_type.value, default={}
    )
    app_id = dedicated_app.get("id")
    installation_id = dedicated_app.get("installation_id")
    pem_exists = "pem" in dedicated_app
    if app_id and installation_id and pem_exists:
        actual_token = get_github_integration_token(
            service,
            app_id=app_id,
            installation_id=installation_id,
            pem_path=f"yaml+file://{service}.dedicated_apps.{token_type.value}.pem",
        )
        return Token(key=actual_token, username=f"{token_type.value}_dedicated_app")
    return None


def get_token_type_from_config(service: str, token_type: TokenType) -> Token | None:
    """Gets the TokenType credentials configured for this `service` in the install config (YAML).
    [All providers] Configuration are defined as a `bot` per TokenType.
    [GitHub] Can also have a `dedicated_app`. `dedicated_app` is preferred.
    """
    if service in ["github", "github_enterprise"]:
        dedicated_app_config = get_dedicated_app_token_from_config(service, token_type)
        if dedicated_app_config:
            return dedicated_app_config

    return get_config(service, "bots", token_type.value)
