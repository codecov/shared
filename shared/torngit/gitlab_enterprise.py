import os

from shared.torngit.gitlab import Gitlab

from shared.config import get_config


class GitlabEnterprise(Gitlab):
    service = "gitlab_enterprise"

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
