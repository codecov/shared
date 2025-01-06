import logging
from typing import Optional

from redis import Redis, RedisError

from shared.django_apps.codecov_auth.models import Owner
from shared.django_apps.core.models import Repository

log = logging.getLogger(__name__)

RATE_LIMIT_REDIS_KEY_PREFIX = "rate_limited_entity_"


def gh_app_key_name(installation_id: int, app_id: str | int | None = None) -> str:
    if app_id is None:
        return f"default_app_{installation_id}"
    return f"{app_id}_{installation_id}"


def owner_key_name(owner_id: int) -> str:
    return str(owner_id)


def default_bot_key_name() -> str:
    return "github_bot"


def determine_entity_redis_key(
    owner: Owner | None, repository: Repository | None
) -> Optional[str]:
    """
    This function will determine the entity that uses a token to
    communicate with third party services, currently Github.

    If no owner is provided, it returns a preset key for github bots.
    Then, it gathers authentication information through the auth_info adapter method
    and returns a GH app id + installation ids if an app exists, otherwise it will return
    the owner who's token it uses.

    The entity can be any of the following:
    <app_id>_<installation_id> for Github Apps
    <owner_id> for Owners
    <TokenType> for mapped Tokens if available
    github_bot for Anonymous users

    It should only be used for github git instances
    """
    from shared.bots import get_adapter_auth_information
    from shared.bots.types import AdapterAuthInformation

    if not owner:
        return default_bot_key_name()

    if repository:
        auth_info: AdapterAuthInformation = get_adapter_auth_information(
            owner=owner, repository=repository
        )
    else:
        auth_info: AdapterAuthInformation = get_adapter_auth_information(owner=owner)

    if (
        auth_info
        and auth_info.get("token")
        and auth_info.get("token").get("entity_name")
    ):
        return auth_info.get("token").get("entity_name")


def determine_if_entity_is_rate_limited(redis_connection: Redis, key_name: str) -> bool:
    """
    This function will determine if a customer is rate limited. It will
    return true if the record exists, false otherwise.
    This will be used by API and Worker and should only be used for github git instances.
    """
    try:
        return redis_connection.exists(f"{RATE_LIMIT_REDIS_KEY_PREFIX}{key_name}")
    except RedisError:
        log.exception(
            "Failed to check if the key name is rate_limited due to RedisError",
            extra=dict(key_name=key_name),
        )
        return False


def set_entity_to_rate_limited(
    redis_connection: Redis, key_name: str, ttl_seconds: int
):
    """
    Marks an entity as rate-limited in Redis. This will be mainly used
    in worker during communication with Github 3rd party services

    @param `key_name` - name of the entity being rate limited. This is found in determine_entity_redis_key
    and in the Token object definition
    key_name can take the shapes of:
    <app_id>_<installation_id> for Github Apps
    <owner_id> for Owners
    <GITHUB_BOT_KEY> for Anonymous users

    @param `ttl_seconds` - Should come from GitHub (in the request that was rate limited)
    """
    if ttl_seconds <= 0:
        # ttl_seconds is the time until the RateLimit ends
        # Makes no sense to mark an installation rate limited if it's not anymore
        return
    try:
        redis_connection.set(
            name=f"rate_limited_entity_{key_name}",
            value=1,
            ex=ttl_seconds,
        )
    except RedisError:
        log.exception(
            "Failed to mark entity as rate_limited due to RedisError",
            extra=dict(entity_id=key_name),
        )
