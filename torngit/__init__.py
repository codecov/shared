from github import Github
# from github_enterprise import *
# from gitlab import *
# from gitlab_enterprise import *
# from bitbucket import *
# from bitbucket_server import *


def get(scm, *a, **k):
    if scm == 'github':
        return Github(*a, **k)
