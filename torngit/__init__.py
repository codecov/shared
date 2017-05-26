import os

from github import Github
from github_enterprise import GithubEnterprise
from gitlab import Gitlab
from gitlab_enterprise import GitlabEnterprise
from gitlab3 import Gitlab as Gitlab3
from gitlab_enterprise3 import GitlabEnterprise as GitlabEnterprise3
from bitbucket import Bitbucket
from bitbucket_server import BitbucketServer


def get(git, async=True, **data):
    if git == 'github':
        return Github.new(async=async, **data)
    elif git == 'github_enterprise':
        return GithubEnterprise.new(async=async, **data)
    elif git == 'bitbucket':
        return Bitbucket.new(async=async, **data)
    elif git == 'bitbucket_server':
        return BitbucketServer.new(async=async, **data)
    elif os.getenv('GITLAB_HOTFIX_PULL_REQUEST_ID'):
        if git == 'gitlab':
            return Gitlab3.new(async=async, **data)
        elif git == 'gitlab_enterprise':
            return GitlabEnterprise3.new(async=async, **data)
    elif git == 'gitlab':
        return Gitlab.new(async=async, **data)
    elif git == 'gitlab_enterprise':
        return GitlabEnterprise.new(async=async, **data)
