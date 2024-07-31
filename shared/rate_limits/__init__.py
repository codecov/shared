import logging
from typing import Optional

from redis import Redis, RedisError

from shared.config import get_config
from shared.django_apps.codecov_auth.models import Owner
from shared.django_apps.core.models import Repository
from shared.typings.torngit import TorngitInstanceData

log = logging.getLogger(__name__)


def gh_app_key_name(installation_id: int, app_id: Optional[int] = None) -> str:
    app_id = app_id or "default_app"
    return f"{app_id}_{installation_id}"


def owner_key_name(owner_id: int) -> str:
    return str(owner_id)


def bot_key_name() -> str:
    return str(get_config("github", "bot", "key"))


# TODO: Test this
def determine_entity_redis_key_from_torngit_data(data: TorngitInstanceData) -> str:
    """
    Determines entity redis key from torngit data. This is an alternative
    function to determine_entity_redis_key if the auth information has been
    parsed into a torngit instance data object.

    It should only be used for github git instances
    """
    current_installation = data.get("installation")
    current_owner = data.get("owner")

    if current_installation and current_installation.get("installation_id"):
        return gh_app_key_name(
            app_id=current_installation.get("app_id"),
            installation_id=current_installation.get("installation_id"),
        )
    elif current_owner and current_owner.get("ownerid"):
        return owner_key_name(owner_id=current_owner.get("ownerid"))
    else:
        return bot_key_name()


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

    It should only be used for github git instances
    """
    from shared.bots import get_adapter_auth_information
    from shared.bots.types import AdapterAuthInformation

    if not owner:
        return bot_key_name()

    if repository:
        auth_info: AdapterAuthInformation = get_adapter_auth_information(
            owner=owner, repository=repository
        )
    else:
        auth_info: AdapterAuthInformation = get_adapter_auth_information(owner=owner)

    if auth_info.get("selected_installation_info"):
        return gh_app_key_name(
            app_id=auth_info.get("selected_installation_info").get("app_id"),
            installation_id=auth_info.get("selected_installation_info").get(
                "installation_id"
            ),
        )
    return owner_key_name(owner_id=auth_info.get("token_owner").ownerid)


def determine_if_entity_is_rate_limited(redis_connection: Redis, key_name: str) -> bool:
    """
    This function will determine if a customer is rate limited. It will
    return true if the record exists, false otherwise.
    This will be used by API and Worker and should only be used for github git instances.
    """
    try:
        return redis_connection.exists(f"rate_limited_entity_{key_name}")
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
