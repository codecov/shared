import os
import unittest
import requests
from ddt import ddt, data

from scms import Github
from scms.github.github import is_merge_commit


@ddt
class Test(unittest.TestCase):
    @data(('stevepeak', 'not-a-repo', 'a'*40, 'no-branch', None),
          ('codecov', 'ci-repo', 'c05f02f66f2e411bd0c6075b0fbd7e344fe5b64e', None, None),
          ('codecov', 'ci-repo', '666f423214c1b2f0f70a8abfaecc45f335e6ce23', None, {'open': True, 'base': {'commit': u'c05f02f66f2e411bd0c6075b0fbd7e344fe5b64e', 'branch': u'master'}, 'head': {'commit': u'666f423214c1b2f0f70a8abfaecc45f335e6ce23', 'branch': u'pr'}, 'id': 4, 'number': 4}),
          ('codecov', 'ci-repo', '2202635bebf2c8247b869a21e354b4cc68c5761c', None, {'open': True, 'base': {'commit': u'c05f02f66f2e411bd0c6075b0fbd7e344fe5b64e', 'branch': u'master'}, 'head': {'commit': u'666f423214c1b2f0f70a8abfaecc45f335e6ce23', 'branch': u'pr'}, 'id': 4, 'number': 4}),
          )
    def test_find_pull_request(self, (owner, repo, sha, branch, equals)):
        res = Github(None, owner, repo).find_pull_request(sha, branch)
        assert res == equals

    @data(('5f724d43330159105a94dce7837ef37085e9891a', ('pending', None)),
          ('60659e225d93358a691f8faad0961fd405f07c87', ('failure', None)),  # these got switched... ugh
          ('d93ba1340854a5adfdc0ce1ba6f21f20d9bbe2b8', ('success', None)),  # these got switched... ugh
          ('d8cfd1631e003fb77af41ecb1ca897c4dd4dd794', ('pending', None)),
          ('3f631de4364b9ead2cc593ee32bb6c1540964597', ('success', None)),
          ('e7f904f0f7698566dcfb7e0e62eddc91e3df7995', ('failure', None)),
          ('00bdac70ec8cda761d01920714f7751e9d4c664c', ('builds', 'success')),
          ('notaref', ('builds', None)),
          ('e7dd243fa92266ac35da5828a688db704018044e', ('success', None)),
          ('a'*40, ('builds', None)))
    def test_get_commit_status(self, (commit, result)):
        res = Github(23162118, 'codecov', 'ci-repo').get_commit_status(commit)
        assert res == result

    @data(('2202635bebf2c8247b869a21e354b4cc68c5761c', True), ('666f423214c1b2f0f70a8abfaecc45f335e6ce23', False))
    def test_is_merge_commit(self, (sha, boolean)):
        res = requests.get("https://api.github.com/repos/codecov/ci-repo/commits/%s?access_token=%s" % (sha, os.getenv("GITHUB_ACCESS_TOKEN")))
        assert res.status_code == 200
        result = bool(is_merge_commit(res.json()['commit']['message']))
        assert result is boolean

    @data(('e7dd243fa92266ac35da5828a688db704018044e', '23e1630df2f1dd9a16462b881d1c89c778a5954f'),
          ('23e1630df2f1dd9a16462b881d1c89c778a5954f', None),
          ('5f724d43330159105a94dce7837ef37085e9891a', None))
    def test_get_merge_commit_head(self, (commit, head)):
        res = Github(23162118, 'codecov', 'ci-repo').get_merge_commit_head(commit)
        assert res == head

    def test_post_comment(self):
        assert Github(None, 'stevepeak', 'not-a-repo').post_comment(1, "Hello world") is None

    def test_edit_comment(self):
        assert Github(None, 'stevepeak', 'not-a-repo').edit_comment(1, 1, "Hello world") is None

    def test_post_status(self):
        assert Github(None, 'stevepeak', 'not-a-repo').post_status('a' * 40, 'success', "context", "Hello world") is None

    def test_get_pull_request_fail(self):
        assert Github(None, 'stevepeak', 'not-a-repo').get_pull_request("1") is None

    def test_get_pull_request(self):
        assert Github(None, 'codecov', 'ci-repo').get_pull_request("4") == {'base': {'branch': u'master', 'commit': u'c05f02f66f2e411bd0c6075b0fbd7e344fe5b64e'}, 'head': {'branch': u'pr', 'commit': u'666f423214c1b2f0f70a8abfaecc45f335e6ce23'}, 'number': '4', 'id': '4', 'open': True}

    def test_get_open_prs(self):
        assert Github(None, 'codecov', 'example-python').get_open_prs() == []  # this may fail because prs exist, but unlikely.
        assert Github(None, 'codecov', 'ci-repo').get_open_prs() == [('#6', '67732246e64b43f37bfc90d843e50ada1b8b1f89'), ('#4', '666f423214c1b2f0f70a8abfaecc45f335e6ce23'), ('#3', '837973ab1fcdd5b5bb7649d82738ce00c9fe76d3')]

    def test_handle_error_with_username(self):
        gh = Github(None, None, None, token=dict(email="ci@codecov.io", username="robot", key='a'))
        res = requests.get("https://api.github.com/repos/codecov/codecov.io?access_token=not-real")
        assert 'ratelimit' in gh.handle_error(res)

    def test_handle_error_without_username(self):
        gh = Github(None, None, None, token=dict(email="ci@codecov.io", key='a'))
        res = requests.get("https://api.github.com/repos/codecov/codecov.io?access_token=not-real")
        assert 'ratelimit' in gh.handle_error(res)

    def test_edit_comment_fail(self):
        assert Github(None, 'codecov', 'ci-repo').edit_comment(4, 73707220, "Hello world") is None

    def test_create_webhook(self):
        # https://developer.github.com/v3/repos/hooks/#list-hooks
        for hook in requests.get('https://api.github.com/repos/codecov/ci-repo/hooks?access_token=' + os.getenv("GITHUB_ACCESS_TOKEN")).json():
            if 'localhost' in hook['config'].get('url', ''):
                # https://developer.github.com/v3/repos/hooks/#delete-a-hook
                requests.delete('https://api.github.com/repos/codecov/ci-repo/hooks/%s?access_token=%s' % (str(hook['id']), os.getenv("GITHUB_ACCESS_TOKEN")))

        hook = Github(None, 'codecov', 'ci-repo').create_hook()
        assert hook is not None
        # https://developer.github.com/v3/repos/hooks/#get-single-hook
        res = requests.get('https://api.github.com/repos/codecov/ci-repo/hooks/%s?access_token=%s' % (str(hook), os.getenv("GITHUB_ACCESS_TOKEN")))
        assert res.status_code == 200
        data = res.json()
        assert 'webhooks/github' in data['config']['url']
        assert sorted(data['events']) == ['delete', 'public', 'pull_request', 'push']

    def test_commits(self):
        commits = Github(None, 'codecov', 'ci-repo').get_commits(pr='6')
        assert commits[0] == '5f724d43330159105a94dce7837ef37085e9891a'
        assert commits[-1] == '67732246e64b43f37bfc90d843e50ada1b8b1f89'

    def test_get_diff(self):
        patch = Github(None, 'codecov', 'ci-repo').get_diff('0028015f7fa260f5fd68f78c0deffc15183d955e', 'c05f02f66f2e411bd0c6075b0fbd7e344fe5b64e')
        assert patch == "diff --git a/README.md b/README.md\n"\
                        "index 7974a22..e89515f 100644\n"\
                        "--- a/README.md\n"\
                        "+++ b/README.md\n"\
                        "@@ -13,3 +13,4 @@\n"\
                        " [2]: https://twitter.com/codecov\n"\
                        " [3]: mailto:hello@codecov.io\n"\
                        " \n"\
                        "+> revenge is best served cold. Love is best served hot.\n"\
                        ""

    def test_get_diff_none(self):
        assert Github(None, 'codecov', 'ci-repo').get_diff('0028015f7fa260f5fd68f78c0deffc15183d955e', 'aaa') is None
        assert Github(None, 'codecov', 'ci-repo').get_diff('a' * 40) is None

    def test_get_commit(self):
        commit = Github(None, 'codecov', 'ci-repo').get_commit('0028015f7fa260f5fd68f78c0deffc15183d955e')
        assert commit == {'date': '2014-10-19T14:32:33Z',
                          'author_login': 'stevepeak',
                          'author_name': 'stevepeak',
                          'author_email': 'steve@stevepeak.net',
                          'author_id': '2041757'}

    def test_get_commit_not_found(self):
        commit = Github(None, 'codecov', 'ci-repo').get_commit('none')
        assert commit is None

    def test_branches(self):
        branches = sorted(Github(None, 'codecov', 'ci-repo').get_branches())
        assert map(lambda a: a[0], branches) == ['for-diffs', 'gh-status-checks', 'master', 'other-branch', 'pr', 'staging', 'status-check', 'stevepeak-patch-1']

        branches = Github(None, 'twisted', 'twisted').get_branches()
        assert len(branches) > 1000

    def test_branches_none(self):
        assert Github(None, 'codecov', 'bla-blah').get_branches() is None
