from github import Github
from github_enterprise import GithubEnterprise
from gitlab import Gitlab
from gitlab_enterprise import GitlabEnterprise
from bitbucket import Bitbucket
from bitbucket_server import BitbucketServer


def get(git, **data):
    if git == 'github':
        return Github.new(**data)
    elif git == 'github_enterprise':
        return GithubEnterprise.new(**data)
    elif git == 'bitbucket':
        return Bitbucket.new(**data)
    elif git == 'bitbucket_server':
        return BitbucketServer.new(**data)
    elif git == 'gitlab':
        return Gitlab.new(**data)
    elif git == 'gitlab_enterprise':
        return GitlabEnterprise.new(**data)
