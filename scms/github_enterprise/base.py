from github_enterprise import GithubEnterpriseBase
from app.services.github.base import GithubHandler


class GithubEnterpriseHandler(GithubHandler, GithubEnterpriseBase):
    pass
