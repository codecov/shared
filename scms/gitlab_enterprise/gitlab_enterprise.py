import os

from app.services.gitlab.gitlab import GitlabBase, GitlabEngine


class GitlabEnterpriseBase(GitlabBase):
    service = 'gitlab_enterprise'
    service_url = os.getenv('GITLAB_ENTERPRISE_URL', '')
    verify_ssl = os.getenv('GITLAB_ENTERPRISE_SSL_PEM') or (os.getenv('GITLAB_ENTERPRISE_VERIFY_SSL') != 'FALSE')


class GitlabEnterpriseEngine(GitlabEngine, GitlabEnterpriseBase):
    pass
