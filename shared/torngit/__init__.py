from shared.torngit.bitbucket import Bitbucket
from shared.torngit.bitbucket_server import BitbucketServer
from shared.torngit.github import Github
from shared.torngit.github_enterprise import GithubEnterprise
from shared.torngit.gitlab import Gitlab
from shared.torngit.gitlab_enterprise import GitlabEnterprise


def get(git, **data):
    if git == "github":
        return Github(**data)
    elif git == "github_enterprise":
        return GithubEnterprise(**data)
    elif git == "bitbucket":
        return Bitbucket(**data)
    elif git == "bitbucket_server":
        return BitbucketServer(**data)
    elif git == "gitlab":
        return Gitlab(**data)
    elif git == "gitlab_enterprise":
        return GitlabEnterprise(**data)
