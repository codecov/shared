import os

from shared.torngit.gitlab import Gitlab

from shared.config import get_config


class GitlabEnterprise(Gitlab):
    service = "gitlab_enterprise"

    @property
    def service_url(self):
        return get_config("gitlab_enterprise", "url")

    @property
    def api_url(self):
        if get_config("gitlab_enterprise", "api_url"):
            return get_config("gitlab_enterprise", "api_url")
        return self.service_url + "/api/v4"

    verify_ssl = os.getenv("GITLAB_ENTERPRISE_SSL_PEM") or (
        os.getenv("GITLAB_ENTERPRISE_VERIFY_SSL") != "FALSE"
    )
