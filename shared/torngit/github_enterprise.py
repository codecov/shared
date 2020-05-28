import os

from shared.torngit.github import Github

from shared.config import get_config


class GithubEnterprise(Github):
    # https://developer.github.com/v3/enterprise/#endpoint-urls

    @classmethod
    def get_service_url(cls):
        return get_config("github_enterprise", "url").strip("/")

    @property
    def service_url(self):
        return self.get_service_url()

    @classmethod
    def get_api_url(cls):
        if get_config("github_enterprise", "api_url"):
            return get_config("github_enterprise", "api_url").strip("/")
        return cls.get_service_url() + "/api/v3"

    @property
    def api_url(self):
        return self.get_api_url()

    service = "github_enterprise"
    verify_ssl = os.getenv("GITHUB_ENTERPRISE_SSL_PEM") or (
        os.getenv("GITHUB_ENTERPRISE_VERIFY_SSL") != "FALSE"
    )
