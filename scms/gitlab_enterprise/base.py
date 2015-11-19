from gitlab_enterprise import GitlabEnterpriseBase
from app.services.gitlab.base import GitlabHandler


class GitlabEnterpriseHandler(GitlabHandler, GitlabEnterpriseBase):
    pass
