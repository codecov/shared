import logging

from redis import Redis, RedisError

from shared.bots import get_adapter_auth_information
from shared.bots.types import AdapterAuthInformation
from shared.config import get_config
from shared.django_apps.codecov_auth.models import Owner
from shared.django_apps.core.models import Repository

log = logging.getLogger(__name__)


# Ensure service = "gh" before using
def determine_entity_redis_key(
    owner: Owner | None, repository: Repository | None
) -> str:
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
    GITHUB_BOT_KEY for Anonymous users
    """
    if not owner:
        return str(get_config("github", "bot", "key"))

    if repository:
        auth_info: AdapterAuthInformation = get_adapter_auth_information(
            owner=owner, repository=repository
        )
    else:
        auth_info: AdapterAuthInformation = get_adapter_auth_information(owner=owner)

    if auth_info.get("selected_installation_info"):
        return f"{auth_info.get("selected_installation_info").get("app_id")}_{auth_info.get("selected_installation_info").get("installation_id")}"
    # How to treat gh app fallbacks?
    else:
        return str(auth_info.get("token_owner").ownerid)


# Ensure service = "gh" before using
def determine_if_entity_is_rate_limited(redis_connection: Redis, key_name: str) -> bool:
    """
    This function will determine if a customer is rate limited. It will
    return true if the record exists, false otherwise.
    This will be used by API and Worker
    """
    return True if redis_connection.get(f"rate_limited_entity_{key_name}") else False


def set_entity_to_rate_limited(redis_connection, key_name: str, ttl_seconds: int):
    """
    This function will set a key to be rate limited. This will be mainly used
    in worker during communication with Github 3rd party services

    key_name can take the shapes of:
    <app_id>_<installation_id> for Github Apps
    <owner_id> for Owners
    GITHUB_BOT_KEY for Anonymous users
    """
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
