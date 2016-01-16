from scms.github.handler import Github
from github_enterprise import GithubEnterprise


class GithubEnterpriseHandler(GithubEnterprise, Github):
    pass
