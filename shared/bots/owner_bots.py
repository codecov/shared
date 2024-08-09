import logging

from shared.bots.exceptions import OwnerWithoutValidBotError
from shared.bots.github_apps import get_github_app_token
from shared.bots.types import TokenWithOwner
from shared.django_apps.codecov_auth.models import Owner, Service
from shared.encryption.oauth import get_encryptor_from_configuration
from shared.rate_limits import owner_key_name
from shared.typings.oauth_token_types import Token
from shared.typings.torngit import GithubInstallationInfo

encryptor = get_encryptor_from_configuration()

log = logging.getLogger(__name__)


def get_owner_or_appropriate_bot(owner: Owner, repoid: int | None = None) -> Owner:
    if owner.bot is not None and owner.bot.oauth_token is not None:
        log.info(
            "Owner has specific bot",
            extra=dict(botid=owner.bot.ownerid, ownerid=owner.ownerid, repoid=repoid),
        )
        return owner.bot
    elif owner.oauth_token is not None:
        log.info(
            "No bot, using owner", extra=dict(ownerid=owner.ownerid, repoid=repoid)
        )
        return owner
    raise OwnerWithoutValidBotError()


def get_owner_appropriate_bot_token(
    owner, installation_info: GithubInstallationInfo | None = None
) -> TokenWithOwner:
    if installation_info:
        result = get_github_app_token(Service(owner.service), installation_info)
        return result

    token_owner = get_owner_or_appropriate_bot(owner)
    token: Token = encryptor.decrypt_token(token_owner.oauth_token)
    token["entity_name"] = owner_key_name(owner_id=token_owner.ownerid)
    return token, token_owner
