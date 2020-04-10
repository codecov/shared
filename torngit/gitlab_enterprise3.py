import os

from torngit.gitlab3 import Gitlab


class GitlabEnterprise(Gitlab):
    service = 'gitlab_enterprise'
    service_url = os.getenv('GITLAB_ENTERPRISE_URL', '').strip('/')
    api_url = os.getenv('GITLAB_ENTERPRISE_API_URL', '').strip('/') or (
        os.getenv('GITLAB_ENTERPRISE_URL', '').strip('/') + '/api/v3')
    verify_ssl = os.getenv('GITLAB_ENTERPRISE_SSL_PEM') or (
        os.getenv('GITLAB_ENTERPRISE_VERIFY_SSL') != 'FALSE')
