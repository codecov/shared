import os

from shared.config import get_config
from shared.torngit.gitlab import Gitlab


class GitlabEnterprise(Gitlab):
    service = "gitlab_enterprise"

    @property
    def redirect_uri(self):
        from_config = get_config("gitlab_enterprise", "redirect_uri", default=None)
        if from_config is not None:
            return from_config
        base = get_config("setup", "codecov_url", default="https://codecov.io")
        return base + "/login/gle"

    @classmethod
    def get_service_url(cls):
        return get_config("gitlab_enterprise", "url")

    @property
    def service_url(self):
        return self.get_service_url()

    @classmethod
    def get_api_url(cls):
        if get_config("gitlab_enterprise", "api_url"):
            return get_config("gitlab_enterprise", "api_url")
        return cls.get_service_url() + "/api/v4"

    @property
    def api_url(self):
        return self.get_api_url()

    verify_ssl = os.getenv("GITLAB_ENTERPRISE_SSL_PEM") or (
        os.getenv("GITLAB_ENTERPRISE_VERIFY_SSL") != "FALSE"
    )
