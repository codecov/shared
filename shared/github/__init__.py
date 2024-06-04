import logging
from time import time
from typing import Literal, Optional
from urllib.parse import urlparse

import jwt
import requests
from redis import Redis, RedisError

import shared.torngit as torngit
from shared.config import get_config, load_file_from_path_at_config

log = logging.getLogger(__name__)

loaded_pems = None

pem_paths = {
    "github": ("github", "integration", "pem"),
    "github_enterprise": ("github_enterprise", "integration", "pem"),
}


def load_pem_from_path(pem_path: str) -> str:
    parsed_path = urlparse(pem_path)
    if parsed_path.scheme == "yaml+file":
        # The URL is a path to a key in the YAML
        # The key's value points to a file mounted in the FS
        path = parsed_path.netloc.split(".")
        return load_file_from_path_at_config(*path)
    raise Exception("Unknown schema to load PEM")


def get_pem(*, pem_name: Optional[str] = None, pem_path: Optional[str] = None) -> str:
    if pem_path:
        return load_pem_from_path(pem_path)
    if pem_name:
        path = pem_paths[pem_name]
        return load_file_from_path_at_config(*path)
    raise Exception("No PEM provided to get installation token")


InstallationErrorCause = Literal["installation_not_found"] | Literal["permission_error"]


class InvalidInstallationError(Exception):
    def __init__(self, error_cause: InstallationErrorCause, *args: object) -> None:
        super().__init__(*args)
        self.error_cause = error_cause


def get_github_jwt_token(
    service: str, app_id: Optional[str] = None, pem_path: Optional[str] = None
) -> Optional[str]:
    # https://developer.github.com/apps/building-github-apps/authenticating-with-github-apps/
    now = int(time())
    payload = {
        # issued at time
        "iat": now,
        # JWT expiration time (max 10 minutes)
        "exp": now + int(get_config(service, "integration", "expires", default=500)),
        # Integration's GitHub identifier
        "iss": app_id or get_config(service, "integration", "id"),
    }
    pem_kwargs = dict(pem_path=pem_path) if pem_path else dict(pem_name=service)
    return jwt.encode(payload, get_pem(**pem_kwargs), algorithm="RS256")


def get_github_integration_token(
    service,
    integration_id=None,
    app_id: Optional[str] = None,
    pem_path: Optional[str] = None,
) -> Optional[str]:
    # https://developer.github.com/apps/building-github-apps/authenticating-with-github-apps/
    token = get_github_jwt_token(service, app_id, pem_path)
    if integration_id:
        if service == "github":
            api_endpoint = torngit.Github.get_api_url()
            host_override = torngit.Github.get_api_host_header()
            url = torngit.Github.count_and_get_url_template(
                url_name="get_github_integration_token"
            ).substitute(api_endpoint=api_endpoint, integration_id=integration_id)
        else:
            api_endpoint = torngit.GithubEnterprise.get_api_url()
            host_override = torngit.GithubEnterprise.get_api_host_header()
            url = torngit.GithubEnterprise.count_and_get_url_template(
                url_name="get_github_integration_token"
            ).substitute(api_endpoint=api_endpoint, integration_id=integration_id)

        headers = {
            "Accept": "application/vnd.github.machine-man-preview+json",
            "User-Agent": "Codecov",
            "Authorization": "Bearer %s" % token,
        }
        if host_override is not None:
            headers["Host"] = host_override

        res = requests.post(url, headers=headers)
        if res.status_code in (404, 403):
            error_cause: InstallationErrorCause = (
                "installation_not_found"
                if res.status_code == 404
                else "permission_error"
            )
            log.warning(
                "Integration could not be found to fetch token from or unauthorized",
                extra=dict(
                    git_service=service,
                    integration_id=integration_id,
                    api_endpoint=api_endpoint,
                    error_cause=error_cause,
                ),
            )
            raise InvalidInstallationError(error_cause)
        try:
            res.raise_for_status()
        except requests.exceptions.HTTPError:
            log.exception(
                "Github Integration Error on service %s",
                service,
                extra=dict(code=res.status_code, text=res.text),
            )
            raise
        res_json = res.json()
        log.info(
            "Requested and received a Github Integration token",
            extra=dict(
                expires_at=res_json.get("expires_at"),
                permissions=res_json.get("permissions"),
                repository_selection=res_json.get("repository_selection"),
                integration_id=integration_id,
            ),
        )
        return res_json["token"]
    else:
        return token


def mark_installation_as_rate_limited(
    redis_connection: Redis,
    installation_id: int,
    ttl_seconds: int,
    app_id: Optional[int],
) -> None:
    """Marks a installation as being rate-limited in Redis.
    Use is_installation_rate_limited to check if it is rate-limited or not.

    @param `installation_id` - GithubAppInstallation.installation_id OR owner.integration_id
    @param `app_id` - GithubAppInstallation.app_id OR 'default_app'
    @param `ttl_seconds` - Should come from GitHub (in the request that was rate limited)

    We require the `app_id` as well because it's possible (albeit unlikely) that 2 installation_id are
    the same for different apps.
    """
    if ttl_seconds <= 0:
        # ttl_seconds is the time until the RateLimit ends
        # Makes no sense to mark an installation rate limited if it's not anymore
        return
    app_id = app_id or "default_app"
    try:
        redis_connection.set(
            name=f"rate_limited_installations_{app_id}_{installation_id}",
            value=1,
            ex=ttl_seconds,
        )
    except RedisError:
        log.exception(
            "Failed to mark installation ID as rate_limited due to RedisError",
            extra=dict(installation_id=installation_id),
        )


def is_installation_rate_limited(
    redis_connection: Redis, installation_id: int, app_id: Optional[int] = None
) -> bool:
    app_id = app_id or "default_app"
    try:
        return redis_connection.exists(
            f"rate_limited_installations_{app_id}_{installation_id}"
        )
    except RedisError:
        log.exception(
            "Failed to check if installation ID is rate_limited due to RedisError",
            extra=dict(installation_id=installation_id),
        )
        return False
