import os
import random
import requests
from tornado.httpclient import HTTPError
from tornado.testing import AsyncTestCase, gen_test

from torngit import Github


class Test(AsyncTestCase):
    headers = {"Authorization": "token %s" % os.getenv("GITHUB_ACCESS_TOKEN")}

    def setUp(self):
        super(Test, self).setUp()
        self.gh = Github(None, 'torngit', 'ci', ioloop=self.io_loop)

    def make_commit(self):
        # https://developer.github.com/v3/git/commits/#create-a-commit
        sha = requests.post("https://api.github.com/repos/torngit/ci/git/commits", headers=self.headers,
                            data='{"message":"ci","tree":"25fc45bb68028118bdc6f65be185784858f339b6","parents":["99b53601f852ecc70d50dd10e172f6b7f101bbbc"]}').json()['sha']
        return sha

    def make_merge_commit(self):
        # https://developer.github.com/v3/git/commits/#create-a-commit
        sha1 = requests.post("https://api.github.com/repos/torngit/ci/git/commits", headers=self.headers,
                             data='{"message":"ci","tree":"25fc45bb68028118bdc6f65be185784858f339b6","parents":["99b53601f852ecc70d50dd10e172f6b7f101bbbc"]}').json()['sha']

        sha2 = requests.post("https://api.github.com/repos/torngit/ci/git/commits", headers=self.headers,
                             data='{"message":"Merge %s into %s","tree":"25fc45bb68028118bdc6f65be185784858f339b6","parents":["99b53601f852ecc70d50dd10e172f6b7f101bbbc"]}' % (sha1, 'a'*40)).json()['sha']
        return sha2, sha1

    # -------------
    # Pull Requests
    # -------------
    @gen_test
    def test_get_pull_requests_at_sha(self):
        res = yield self.gh.get_pull_requests('9e0ac7c916adc0573014f1d379bdf7ef45acd23e')
        assert res == [(None, '1')]

    @gen_test
    def test_get_pull_requests(self):
        res = yield self.gh.get_pull_requests()
        assert res == [(None, '1')]

    @gen_test
    def test_get_pull_requests_state_closed(self):
        res = yield self.gh.get_pull_requests(state='closed')
        assert res == [(None, '2')]

    @gen_test
    def test_get_pull_requests_state_opened(self):
        res = yield self.gh.get_pull_requests(state='open')
        assert res == [(None, '1')]

    @gen_test
    def test_get_pull_request(self):
        res = yield self.gh.get_pull_request(1)
        assert res == {
            'open': True, 'merged': False, 'id': '1', 'number': '1',
            'base': {'commit': u'99b53601f852ecc70d50dd10e172f6b7f101bbbc', 'branch': u'master'},
            'head': {'commit': u'9e0ac7c916adc0573014f1d379bdf7ef45acd23e', 'branch': u'pr'}
        }

    @gen_test
    def test_get_pull_request_merge_commit(self):
        res = yield self.gh.get_pull_requests('6b7cf45238ec409064893b51f8dfa2f3ce51c99c')
        assert res == [(None, '1')]

    @gen_test
    def test_get_pull_request_sha_not_found(self):
        with self.assertRaises(HTTPError):
            yield self.gh.get_pull_requests('a'*40)

    # ------------
    # Merge Commit
    # ------------
    @gen_test
    def test_get_merge_commit_head_none(self):
        res = yield self.gh._get_merge_commit_head('99b53601f852ecc70d50dd10e172f6b7f101bbbc')
        assert res is None

    @gen_test
    def test_get_merge_commit_head(self):
        res = yield self.gh._get_merge_commit_head('6b7cf45238ec409064893b51f8dfa2f3ce51c99c')
        assert res == '9e0ac7c916adc0573014f1d379bdf7ef45acd23e'

    @gen_test
    def test_get_source(self):
        res = yield self.gh.get_source('readme.md', '99b53601f852ecc70d50dd10e172f6b7f101bbbc')
        assert res['content'] == 'Hello world!\n'

    # -------------
    # Commit Status
    # -------------
    @gen_test
    def test_get_commit_status(self):
        res = yield self.gh.get_commit_status('99b53601f852ecc70d50dd10e172f6b7f101bbbc')
        assert res == 'pending'

    @gen_test
    def test_get_commit_statuses(self):
        res = yield self.gh.get_commit_statuses('99b53601f852ecc70d50dd10e172f6b7f101bbbc')
        self.assertItemsEqual(res._statuses, [{'url': None, 'state': u'pending', 'context': u'other', 'time': u'2015-12-21T16:54:13Z'},
                                              {'url': None, 'state': u'success', 'context': u'ci', 'time': u'2015-12-21T16:54:05Z'}])

    @gen_test
    def test_get_commit_statuses_merge_commit(self):
        sha2 = yield self.gh.get_commit_statuses('6b7cf45238ec409064893b51f8dfa2f3ce51c99c')
        assert sha2 is None

    @gen_test
    def test_set_commit_status(self):
        sha = self.make_commit()
        print(sha)
        res = yield self.gh.set_commit_status(sha, 'success', 'torngit/demo', 'Hello world')
        assert res
        res = requests.get('https://api.github.com/repos/torngit/ci/commits/%s/statuses' % sha, headers=self.headers).json()
        assert len(res) == 1
        assert res[0]['context'] == 'torngit/demo'

    @gen_test
    def test_set_commit_status_merge_commit(self):
        sha, sha2 = self.make_merge_commit()
        res = yield self.gh.set_commit_status(sha, 'success', 'torngit/demo', 'Hello world')
        assert res
        res = requests.get('https://api.github.com/repos/torngit/ci/commits/%s/statuses' % sha, headers=self.headers).json()
        assert len(res) == 1
        assert res[0]['context'] == 'torngit/demo'

        res = requests.get('https://api.github.com/repos/torngit/ci/commits/%s/statuses' % sha2, headers=self.headers).json()
        assert len(res) == 1
        assert res[0]['context'] == 'torngit/demo'

    @gen_test
    def test_post_comment(self):
        r = str(random.random())
        cid = yield self.gh.post_comment(1, r)
        assert int(cid)
        res = requests.get('https://api.github.com/repos/torngit/ci/issues/comments/%s' % cid, headers=self.headers).json()
        assert res['body'] == r
        requests.delete('https://api.github.com/repos/torngit/ci/issues/comments/%s' % cid, headers=self.headers)

    @gen_test
    def test_edit_comment(self):
        r = str(random.random())
        res = yield self.gh.edit_comment(1, 166593320, r)
        assert res
        res = requests.get('https://api.github.com/repos/torngit/ci/issues/comments/166593320', headers=self.headers).json()
        assert res['body'] == r

    @gen_test
    def test_create_webhook(self):
        # https://developer.github.com/v3/repos/hooks/#list-hooks
        for hook in requests.get('https://api.github.com/repos/torngit/ci/hooks', headers=self.headers).json():
            if 'localhost' in hook['config'].get('url', ''):
                # https://developer.github.com/v3/repos/hooks/#delete-a-hook
                requests.delete('https://api.github.com/repos/torngit/ci/hooks/%s' % str(hook['id']), headers=self.headers)

        hook = yield self.gh.post_webhook('http://localhost', ['push'], 'abc123')
        assert hook is not None
        # https://developer.github.com/v3/repos/hooks/#get-single-hook
        res = requests.get('https://api.github.com/repos/torngit/ci/hooks/%s' % str(hook), headers=self.headers)
        assert res.status_code == 200
        data = res.json()
        assert 'http://localhost' == data['config']['url']
        assert sorted(data['events']) == ['push']

    @gen_test
    def test_list_teams(self):
        res = yield self.gh.list_teams()
        assert res == []

        gh = Github(None, None, None,
                    token=dict(key='testgeghyogc7wjiscwy9ms1fjv3q4ds1y7s1dcv', secret='', username='codecov-test'),
                    ioloop=self.io_loop)
        res = yield gh.list_teams()
        assert res == [{'name': 'Codecov', 'id': '8226205', 'email': 'hello@codecov.io', 'username': 'codecov'}]

    @gen_test
    def test_get_authenticated(self):
        res = yield self.gh.get_authenticated()
        assert res == (True, True)

    @gen_test
    def test_get_authenticated_not_admin(self):
        # codecov-test
        gh = Github(None, 'torngit', 'ci',
                    token=dict(key='testgeghyogc7wjiscwy9ms1fjv3q4ds1y7s1dcv', secret='', username='codecov-test'),
                    ioloop=self.io_loop)
        res = yield gh.get_authenticated()
        assert res == (True, False)

    @gen_test
    def test_get_authenticated_404(self):
        with self.assertRaises(HTTPError):
            yield Github(None, 'torngit', '404', ioloop=self.io_loop).get_authenticated()

    @gen_test
    def test_get_authenticated_private(self):
        with self.assertRaises(HTTPError):
            # private repo
            yield Github(None, 'codecov', 'codecov.io', ioloop=self.io_loop).get_authenticated()

    @gen_test
    def test_get_repository(self):
        repo = yield self.gh.get_repository()
        assert repo == {'branch': u'master',
                        'owner_service_id': 16386719,
                        'private': False,
                        'repo': u'ci',
                        'repo_service_id': 48378290,
                        'username': u'torngit'}

    @gen_test
    def test_get_repository_by_id(self):
        self.gh['repo_service_id'] = '48378290'
        repo = yield self.gh.get_repository()
        assert repo == {'branch': u'master',
                        'owner_service_id': 16386719,
                        'private': False,
                        'repo': u'ci',
                        'repo_service_id': 48378290,
                        'username': u'torngit'}

    @gen_test
    def test_list_repos(self):
        repos = yield self.gh.list_repos()
        assert repos == [{'fork': None, 'username': u'torngit', 'branch': u'master', 'repo': u'ci', 'owner_service_id': 16386719, 'private': False, 'repo_service_id': 48378290},
                         {'fork': {'username': u'codecov', 'repo': u'example-python', 'branch': u'master', 'owner_service_id': 8226205, 'private': False, 'repo_service_id': 24344106},
                          'username': u'torngit', 'branch': u'master', 'repo': u'example-python', 'owner_service_id': 16386719, 'private': False, 'repo_service_id': 48430557}]

    @gen_test
    def test_pull_commits(self):
        commits = yield self.gh.get_pull_request_commits('1')
        assert commits == ['9e0ac7c916adc0573014f1d379bdf7ef45acd23e']

    @gen_test
    def test_get_diff(self):
        patch = yield self.gh.get_diff('99b53601f852ecc70d50dd10e172f6b7f101bbbc', '9e0ac7c916adc0573014f1d379bdf7ef45acd23e')
        assert patch == 'diff --git a/readme.md b/readme.md\n'\
                        'index cd08755..e63d842 100644\n'\
                        '--- a/readme.md\n'\
                        '+++ b/readme.md\n'\
                        '@@ -1 +1 @@\n'\
                        '-Hello world!\n'\
                        '+Pull request\n'

    @gen_test
    def test_get_diff_single(self):
        patch = yield self.gh.get_diff('9e0ac7c916adc0573014f1d379bdf7ef45acd23e')
        assert patch == 'diff --git a/readme.md b/readme.md\n'\
                        'index cd08755..e63d842 100644\n'\
                        '--- a/readme.md\n'\
                        '+++ b/readme.md\n'\
                        '@@ -1 +1 @@\n'\
                        '-Hello world!\n'\
                        '+Pull request\n'

    @gen_test
    def test_get_commit(self):
        res = yield self.gh.get_commit('9e0ac7c916adc0573014f1d379bdf7ef45acd23e')
        assert res == {'author_email': u'steve@stevepeak.net',
                       'author_id': '2041757',
                       'author_login': u'stevepeak',
                       'author_name': u'Steve Peak',
                       'date': u'2015-12-21T15:18:35Z',
                       'message': u'create a pr'}

    @gen_test
    def test_get_branches(self):
        res = yield self.gh.get_branches()
        assert res == [(u'closedpr', u'5061da92b04ce307e38cf84a443c36d8831dee45'),
                       (u'master', u'6b7cf45238ec409064893b51f8dfa2f3ce51c99c'),
                       (u'pr', u'9e0ac7c916adc0573014f1d379bdf7ef45acd23e')]

    # def test_get_diff_none(self):
    #     assert Github(None, 'codecov', 'ci-repo').get_diff('0028015f7fa260f5fd68f78c0deffc15183d955e', 'aaa') is None
    #     assert Github(None, 'codecov', 'ci-repo').get_diff('a' * 40) is None

    # def test_get_commit(self):
    #     commit = Github(None, 'codecov', 'ci-repo').get_commit('0028015f7fa260f5fd68f78c0deffc15183d955e')
    #     assert commit == {'date': '2014-10-19T14:32:33Z',
    #                       'author_login': 'stevepeak',
    #                       'author_name': 'stevepeak',
    #                       'author_email': 'steve@stevepeak.net',
    #                       'author_id': '2041757'}

    # def test_get_commit_not_found(self):
    #     commit = Github(None, 'codecov', 'ci-repo').get_commit('none')
    #     assert commit is None

    # def test_branches(self):
    #     branches = sorted(Github(None, 'codecov', 'ci-repo').get_branches())
    #     assert map(lambda a: a[0], branches) == ['for-diffs', 'gh-status-checks', 'master', 'other-branch', 'pr', 'staging', 'status-check', 'stevepeak-patch-1']

    #     branches = Github(None, 'twisted', 'twisted').get_branches()
    #     assert len(branches) > 1000

    # def test_branches_none(self):
    #     assert Github(None, 'codecov', 'bla-blah').get_branches() is None
