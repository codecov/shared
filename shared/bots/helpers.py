import logging
from typing import Self

from pydantic import BaseModel, ValidationError

from shared.bots.exceptions import RepositoryWithoutValidBotError
from shared.config import get_config
from shared.github import InvalidInstallationError
from shared.github import get_github_integration_token as _get_github_integration_token
from shared.torngit.base import TokenType
from shared.typings.oauth_token_types import Token

log = logging.getLogger(__name__)


def get_github_integration_token(
    service: str,
    installation_id: int | None = None,
    app_id: str | None = None,
    pem_path: str | None = None,
):
    try:
        return _get_github_integration_token(
            service,
            integration_id=installation_id,
            app_id=app_id,
            pem_path=pem_path,
        )
    except InvalidInstallationError:
        log.warning("Failed to get installation token")
        raise RepositoryWithoutValidBotError()


class DedicatedApp(BaseModel):
    id: str | int
    installation_id: int
    pem: str

    @classmethod
    def validate_or_none(cls, value: object) -> Self | None:
        try:
            return cls.model_validate(value)
        except ValidationError:
            return None

    def pem_path(self, service: str, token_type: TokenType) -> str:
        return f"yaml+file://{service}.dedicated_apps.{token_type.value}.pem"


def get_dedicated_app_token_from_config(
    service: str, token_type: TokenType
) -> Token | None:
    # GitHub can have 'dedicated_apps', and those are preferred
    dedicated_app = DedicatedApp.validate_or_none(
        get_config(service, "dedicated_apps", token_type.value, default={})
    )
    if dedicated_app is None:
        return None

    actual_token = get_github_integration_token(
        service,
        app_id=str(dedicated_app.id),
        installation_id=dedicated_app.installation_id,
        pem_path=dedicated_app.pem_path(service, token_type),
    )
    return Token(
        key=actual_token,
        username=f"{token_type.value}_dedicated_app",
        entity_name=token_type.value,
    )


def get_token_type_from_config(service: str, token_type: TokenType) -> Token | None:
    """Gets the TokenType credentials configured for this `service` in the install config (YAML).
    [All providers] Configuration are defined as a `bot` per TokenType.
    [GitHub] Can also have a `dedicated_app`. `dedicated_app` is preferred.
    """
    if service in ["github", "github_enterprise"]:
        dedicated_app_config = get_dedicated_app_token_from_config(service, token_type)
        if dedicated_app_config:
            return dedicated_app_config

    token_from_config = get_config(service, "bots", token_type.value)
    if token_from_config:
        token_from_config["entity_name"] = token_type.value
    return token_from_config
