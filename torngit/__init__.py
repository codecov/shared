import os

from torngit.github import Github
from torngit.github_enterprise import GithubEnterprise
from torngit.gitlab import Gitlab
from torngit.gitlab_enterprise import GitlabEnterprise
from torngit.gitlab3 import Gitlab as Gitlab3
from torngit.gitlab_enterprise3 import GitlabEnterprise as GitlabEnterprise3
from torngit.bitbucket import Bitbucket
from torngit.bitbucket_server import BitbucketServer


def get(git, **data):
    if git == 'github':
        return Github(**data)
    elif git == 'github_enterprise':
        return GithubEnterprise(**data)
    elif git == 'bitbucket':
        return Bitbucket(**data)
    elif git == 'bitbucket_server':
        return BitbucketServer(**data)
    elif git == 'gitlab':
        return Gitlab(**data)
    elif git == 'gitlab_enterprise':
        if os.getenv('GITLAB_HOTFIX_PULL_REQUEST_ID') or os.getenv('GITLAB_8'):
            return GitlabEnterprise3(**data)
        else:
            return GitlabEnterprise(**data)
