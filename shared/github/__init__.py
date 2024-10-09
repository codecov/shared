import logging
from time import time
from typing import Literal, Optional
from urllib.parse import urlparse

import jwt
import requests

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


InstallationErrorCause = (
    Literal["installation_not_found"]
    | Literal["permission_error"]
    | Literal["requires_authentication"]
    | Literal["installation_suspended"]
    | Literal["validation_failed_or_spammed"]
    | Literal["rate_limit"]
)


class InvalidInstallationError(Exception):
    def __init__(self, error_cause: InstallationErrorCause, *args: object) -> None:
        super().__init__(error_cause, *args)
        self.error_cause = error_cause


def decide_installation_error_cause(
    response: requests.Response,
) -> InstallationErrorCause:
    # https://docs.github.com/en/rest/apps/apps?apiVersion=2022-11-28#create-an-installation-access-token-for-an-app
    is_suspended = (
        response.json().get("message") == "This installation has been suspended"
    )
    is_rate_limit = (
        "X-RateLimit-Remaining" in response.headers or "Retry-After" in response.headers
    )
    match response.status_code:
        case 401:
            return "requires_authentication"
        case 404:
            return "installation_not_found"
        case 422:
            return "validation_failed_or_spammed"
        case 403:
            if is_suspended:
                return "installation_suspended"
            elif is_rate_limit:
                return "rate_limit"
            else:
                return "permission_error"


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
        if res.status_code in [401, 403, 404, 422]:
            error_cause = decide_installation_error_cause(res)
            log.warning(
                "Integration could not be found to fetch token from or unauthorized",
                extra=dict(
                    git_service=service,
                    integration_id=integration_id,
                    api_endpoint=api_endpoint,
                    error_cause=error_cause,
                    github_error=res.json().get("message"),
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
