import os

from shared.config import get_config
from shared.torngit.github import GITHUB_API_ENDPOINTS, Github


class GithubEnterprise(Github):
    # https://developer.github.com/v3/enterprise/#endpoint-urls

    @classmethod
    def get_service_url(cls):
        return get_config("github_enterprise", "url").strip("/")

    @classmethod
    def get_api_url(cls):
        if get_config("github_enterprise", "api_url"):
            return get_config("github_enterprise", "api_url").strip("/")
        return cls.get_service_url() + "/api/v3"

    @classmethod
    def count_and_get_url_template(self, url_name):
        # Github Enterprise uses the same urls as Github, but has a separate Counter
        GITHUB_API_ENDPOINTS[url_name]["enterprise_counter"].inc()
        return GITHUB_API_ENDPOINTS[url_name]["url_template"]

    service = "github_enterprise"
    verify_ssl = os.getenv("GITHUB_ENTERPRISE_SSL_PEM") or (
        os.getenv("GITHUB_ENTERPRISE_VERIFY_SSL") != "FALSE"
    )
