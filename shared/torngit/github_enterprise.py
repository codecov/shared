import os

from shared.torngit.github import Github


class GithubEnterprise(Github):
    # https://developer.github.com/v3/enterprise/#endpoint-urls
    service = 'github_enterprise'
    service_url = os.getenv('GITHUB_ENTERPRISE_URL', '').strip('/')
    api_url = os.getenv('GITHUB_ENTERPRISE_API_URL', '').strip('/') or (
        os.getenv('GITHUB_ENTERPRISE_URL', '').strip('/') + '/api/v3')
    verify_ssl = os.getenv('GITHUB_ENTERPRISE_SSL_PEM') or (
        os.getenv('GITHUB_ENTERPRISE_VERIFY_SSL') != 'FALSE')
