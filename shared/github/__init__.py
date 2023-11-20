import logging
from datetime import datetime
from time import time
from typing import Optional

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


def get_pem(pem_name: str) -> str:
    path = pem_paths[pem_name]
    return load_file_from_path_at_config(*path)


class InvalidInstallationError(Exception):
    pass


def get_github_integration_token(service, integration_id=None) -> Optional[str]:
    # https://developer.github.com/apps/building-github-apps/authenticating-with-github-apps/
    now = int(time())
    payload = {
        # issued at time
        "iat": now,
        # JWT expiration time (max 10 minutes)
        "exp": now + int(get_config(service, "integration", "expires", default=500)),
        # Integration's GitHub identifier
        "iss": get_config(service, "integration", "id"),
    }
    token = jwt.encode(payload, get_pem(service), algorithm="RS256")
    if integration_id:
        api_endpoint = (
            torngit.Github.get_api_url()
            if service == "github"
            else torngit.GithubEnterprise.get_api_url()
        )
        headers = {
            "Accept": "application/vnd.github.machine-man-preview+json",
            "User-Agent": "Codecov",
            "Authorization": "Bearer %s" % token,
        }
        url = "%s/app/installations/%s/access_tokens" % (api_endpoint, integration_id)
        res = requests.post(url, headers=headers)
        if res.status_code in (404, 403):
            log.warning(
                "Integration could not be found to fetch token from or unauthorized",
                extra=dict(
                    git_service=service,
                    integration_id=integration_id,
                    api_endpoint=api_endpoint,
                ),
            )
            raise InvalidInstallationError()
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
                valid_from=datetime.fromtimestamp(payload["iat"]).isoformat(),
                expires_at=res_json.get("expires_at"),
                permissions=res_json.get("permissions"),
                repository_selection=res_json.get("repository_selection"),
                integration_id=integration_id,
            ),
        )
        return res_json["token"]
    else:
        return token
