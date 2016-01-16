from github import Github
# from github_enterprise import *
# from gitlab import *
# from gitlab_enterprise import *
# from bitbucket import *
# from bitbucket_server import *


def get(git, **data):
    if git == 'github':
        return Github.new(**data)
