import os

from shared.torngit.github import Github

from shared.config import get_config


class GithubEnterprise(Github):
    # https://developer.github.com/v3/enterprise/#endpoint-urls
    @property
    def service_url(self):
        return get_config("github_enterprise", "url").strip("/")

    @property
    def api_url(self):
        if get_config("github_enterprise", "api_url"):
            return get_config("github_enterprise", "api_url").strip("/")
        return self.service_url + "/api/v3"

    service = "github_enterprise"
    verify_ssl = os.getenv("GITHUB_ENTERPRISE_SSL_PEM") or (
        os.getenv("GITHUB_ENTERPRISE_VERIFY_SSL") != "FALSE"
    )
