import pytest

from torngit.gitlab import Gitlab
from torngit.exceptions import TorngitObjectNotFoundError, TorngitClientError


@pytest.fixture
def valid_handler():
    return Gitlab(
        repo=dict(service_id='187725'),
        owner=dict(username='stevepeak'),
        token=dict(
            key='testff3hzs8z959lb15xji4gudqt1ab2n3pnzgbnkxk9ie5ipg82ku2hmet78i5w'
        )
    )


class TestGitlabTestCase(object):

    @pytest.mark.asyncio
    async def test_post_comment(self, valid_handler, codecov_vcr):
        expected_result = {
            'id': 113977323,
            'noteable_id': 59639,
            'noteable_iid': 1,
            'noteable_type': 'MergeRequest',
            'resolvable': False,
            'system': False,
            'type': None,
            'updated_at': '2018-11-02T05:25:09.363Z',
            'attachment': None,
            'author': {
                'avatar_url': 'https://secure.gravatar.com/avatar/dcdb35375db567705dd7e74226fae67b?s=80&d=identicon',
                'name': 'Codecov',
                'state': 'active',
                'id': 109640,
                'username': 'codecov',
                'web_url': 'https://gitlab.com/codecov'
            },
            'body': 'Hello world',
            'created_at': '2018-11-02T05:25:09.363Z'
        }
        res = await valid_handler.post_comment("1", "Hello world")
        assert res['author'] == expected_result['author']
        assert res == expected_result

    @pytest.mark.asyncio
    async def test_edit_comment(self, valid_handler, codecov_vcr):
        res = await valid_handler.edit_comment("1", "113977323", "Hello world number 2")
        assert res is not None
        assert res['id'] == 113977323

    @pytest.mark.asyncio
    async def test_edit_comment_not_found(self, valid_handler, codecov_vcr):
        with pytest.raises(TorngitObjectNotFoundError):
            await valid_handler.edit_comment("1", 113979999, "Hello world number 2")

    @pytest.mark.asyncio
    async def test_delete_comment(self, valid_handler, codecov_vcr):
        assert await valid_handler.delete_comment("1", "113977323") is True

    @pytest.mark.asyncio
    async def test_delete_comment_not_found(self, valid_handler, codecov_vcr):
        with pytest.raises(TorngitObjectNotFoundError):
            await valid_handler.delete_comment("1", 113977999)

    @pytest.mark.asyncio
    async def test_find_pull_request_nothing_found(self, valid_handler, codecov_vcr):
        # nothing matches commit or branch
        assert await valid_handler.find_pull_request('a' * 40, 'no-branch') is None

    @pytest.mark.asyncio
    async def test_find_pull_request_merge_requests_disabled(self, valid_handler, codecov_vcr):
        # merge requests turned off on Gitlab settings
        res = await valid_handler.find_pull_request('a' * 40)
        assert res is None

    @pytest.mark.asyncio
    async def test_find_pull_request_project_not_found(self, valid_handler, codecov_vcr):
        with pytest.raises(TorngitClientError) as excinfo:
            await valid_handler.find_pull_request('a' * 40)
        assert excinfo.value.code == 404

    @pytest.mark.asyncio
    async def test_get_pull_request_fail(self, valid_handler, codecov_vcr):
        with pytest.raises(TorngitObjectNotFoundError):
            await valid_handler.get_pull_request("100")

    get_pull_request_test_data = [
        (
            '1',
            {
                'base': {
                    'branch': u'master',
                },
                'head': {
                    'branch': u'other-branch',
                    'commitid': 'dd798926730aad14aadf72281204bdb85734fe67'
                },
                'number': '1',
                'id': '1',
                'state': 'open',
                'title': 'Other branch'
            }
        ),
    ]

    @pytest.mark.asyncio
    @pytest.mark.parametrize("a,b", get_pull_request_test_data)
    async def test_get_pull_request(self, valid_handler, a, b, codecov_vcr):
        res = await valid_handler.get_pull_request(a)
        assert res == b

    @pytest.mark.asyncio
    async def test_get_pull_request_commits(self, valid_handler, codecov_vcr):
        expected_result = ["dd798926730aad14aadf72281204bdb85734fe67"]
        res = await valid_handler.get_pull_request_commits("1")
        assert res == expected_result

    @pytest.mark.asyncio
    async def test_get_pull_requests(self, valid_handler, codecov_vcr):
        expected_result = [1]
        res = await valid_handler.get_pull_requests()
        assert res == expected_result

    @pytest.mark.asyncio
    async def test_get_commit(self, valid_handler, codecov_vcr):
        commit = await valid_handler.get_commit('0028015f7fa260f5fd68f78c0deffc15183d955e')
        assert commit == {
            'author': {
                'id': None,
                'username': None,
                'email': 'steve@stevepeak.net',
                'name': 'stevepeak'
            },
            'message': 'added large file\n',
            'parents': ['5716de23b27020419d1a40dd93b469c041a1eeef'],
            'commitid': '0028015f7fa260f5fd68f78c0deffc15183d955e',
            'timestamp': '2014-10-19T14:32:33.000Z'
        }

    @pytest.mark.asyncio
    async def test_get_commit_not_found(self, valid_handler, codecov_vcr):
        with pytest.raises(TorngitObjectNotFoundError):
            await valid_handler.get_commit('none')

    @pytest.mark.asyncio
    async def test_get_commit_diff_file_change(self, valid_handler, codecov_vcr):
        expected_result = {
            'files': {
                'large.md': {
                    'before': None,
                    'segments': [{
                        'header': ['0', '0', '1', '816'],
                    }],
                    'stats': {
                        'added': 816,
                        'removed': 0
                    },
                    'type': 'modified'
                }
            }
        }
        res = await valid_handler.get_commit_diff('0028015f7fa260f5fd68f78c0deffc15183d955e')
        assert 'files' in res
        assert 'large.md' in res['files']
        assert 'segments' in res['files']['large.md']
        assert len(res['files']['large.md']['segments']) == 1
        assert 'lines' in res['files']['large.md']['segments'][0]
        assert len(res['files']['large.md']['segments'][0].pop('lines')) == 816
        assert res == expected_result

    @pytest.mark.asyncio
    async def test_get_commit_diff(self, valid_handler, codecov_vcr):
        expected_result = {
            'files': {
                'README.md': {
                    'before': None,
                    'segments': [{
                        'header': ['1', '5', '1', '15'],
                        'lines': [
                            '-### Example', '+### CI Testing', ' ',
                            '-> This repo is used for CI '
                            'Testing. Enjoy this gif as a '
                            'reward!', '+> This repo is used for CI '
                            'Testing', '+', '+', '+| [https://codecov.io/][1] '
                            '| [@codecov][2] | '
                            '[hello@codecov.io][3] |', '+| ------------------------ '
                            '| ------------- | '
                            '--------------------- |', '+', '+-----', '+', '+',
                            '+[1]: https://codecov.io/', '+[2]: '
                            'https://twitter.com/codecov', '+[3]: '
                            'mailto:hello@codecov.io', ' ', '-![i can do '
                            'that](http://gph.is/17cvPc4)'
                        ]
                    }],
                    'stats': {
                        'added': 13,
                        'removed': 3
                    },
                    'type': 'modified'
                }
            }
        }
        res = await valid_handler.get_commit_diff('c739768fcac68144a3a6d82305b9c4106934d31a')
        print(list(res.keys()))
        assert res == expected_result

    @pytest.mark.asyncio
    async def test_get_commit_statuses(self, valid_handler, codecov_vcr):
        res = await valid_handler.get_commit_statuses('c739768fcac68144a3a6d82305b9c4106934d31a')
        assert res == 'success'

    @pytest.mark.asyncio
    async def test_set_commit_status(self, valid_handler, codecov_vcr):
        target_url = 'https://localhost:50036/gitlab/codecov/ci-repo?ref=ad798926730aad14aadf72281204bdb85734fe67'
        expected_result = {
            'allow_failure': False,
            'author': {
                'avatar_url': 'https://secure.gravatar.com/avatar/dcdb35375db567705dd7e74226fae67b?s=80&d=identicon',
                'id': 109640,
                'name': 'Codecov',
                'state': 'active',
                'username': 'codecov',
                'web_url': 'https://gitlab.com/codecov'
            },
            'coverage': None,
            'description': 'aaaaaaaaaa',
            'finished_at': '2018-11-05T20:11:18.137Z',
            'id': 116703167,
            'name': 'context',
            'ref': 'master',
            'sha': 'c739768fcac68144a3a6d82305b9c4106934d31a',
            'started_at': None,
            'status': 'success',
            'target_url': target_url,
            'created_at': '2018-11-05T20:11:18.104Z'
        }
        res = await valid_handler.set_commit_status(
            'c739768fcac68144a3a6d82305b9c4106934d31a',
            'success',
            'context',
            'aaaaaaaaaa',
            target_url
        )
        assert res['author'] == expected_result['author']
        assert res == expected_result

    @pytest.mark.asyncio
    async def test_get_branches(self, valid_handler, codecov_vcr):
        branches = sorted(await valid_handler.get_branches())
        print(branches)
        assert list(map(lambda a: a[0], branches)) == ['master', 'other-branch']

    @pytest.mark.asyncio
    async def test_post_webhook(self, valid_handler, codecov_vcr):
        url = 'http://requestbin.net/r/1ecyaj51'
        name, events, secret = 'a', {'job_events': True}, 'd'
        expected_result = {
            'confidential_issues_events': False,
            'confidential_note_events': None,
            'created_at': '2018-11-06T04:51:57.164Z',
            'enable_ssl_verification': True,
            'id': 422507,
            'issues_events': False,
            'job_events': True,
            'merge_requests_events': False,
            'note_events': False,
            'pipeline_events': False,
            'project_id': 187725,
            'push_events': True,
            'push_events_branch_filter': None,
            'repository_update_events': False,
            'tag_push_events': False,
            'url': 'http://requestbin.net/r/1ecyaj51',
            'wiki_page_events': False,
        }
        res = await valid_handler.post_webhook(name, url, events, secret)
        assert res == expected_result

    @pytest.mark.asyncio
    async def test_edit_webhook(self, valid_handler, codecov_vcr):
        url = 'http://requestbin.net/r/1ecyaj51'
        events = {'tag_push_events': True, 'note_events': True}
        new_name, secret = 'new_name', 'new_secret'
        expected_result = {
            'confidential_issues_events': False,
            'confidential_note_events': None,
            'created_at': '2018-11-06T04:51:57.164Z',
            'enable_ssl_verification': True,
            'id': 422507,
            'issues_events': False,
            'job_events': True,
            'merge_requests_events': False,
            'note_events': True,  # Notice this changed
            'pipeline_events': False,
            'project_id': 187725,
            'push_events': True,
            'push_events_branch_filter': None,
            'repository_update_events': False,
            'tag_push_events': True,  # Notice this changeds
            'url': 'http://requestbin.net/r/1ecyaj51',
            'wiki_page_events': False,
        }
        res = await valid_handler.edit_webhook('422507', new_name, url, events, secret)
        assert res == expected_result

    @pytest.mark.asyncio
    async def test_delete_webhook(self, valid_handler, codecov_vcr):
        res = await valid_handler.delete_webhook('422507')
        assert res is True

    @pytest.mark.asyncio
    async def test_delete_webhook_not_found(self, valid_handler, codecov_vcr):
        with pytest.raises(TorngitObjectNotFoundError):
            await valid_handler.delete_webhook('422507987')

    @pytest.mark.asyncio
    async def test_get_authenticated(self, valid_handler, codecov_vcr):
        res = await valid_handler.get_authenticated()
        assert res == (True, True)

    @pytest.mark.asyncio
    async def test_get_compare(self, valid_handler, codecov_vcr):
        base, head = 'b33e1281', '5716de23'
        expected_result = {
            'diff': {
                'files': {
                    'README.md': {
                        'type': 'modified',
                        'before': None,
                        'segments': [
                            {
                                'header': ['1', '5', '1', '15'],
                                'lines': ['-### Example', '+### CI Testing', ' ', '-> This repo is used for CI Testing. Enjoy this gif as a reward!', '+> This repo is used for CI Testing', '+', '+', '+| [https://codecov.io/][1] | [@codecov][2] | [hello@codecov.io][3] |', '+| ------------------------ | ------------- | --------------------- |', '+', '+-----', '+', '+', '+[1]: https://codecov.io/', '+[2]: https://twitter.com/codecov', '+[3]: mailto:hello@codecov.io', ' ', '-![i can do that](http://gph.is/17cvPc4)']
                            }
                        ],
                        'stats': {
                            'added': 13, 'removed': 3
                        }
                    },
                    'folder/hello-world.txt': {
                        'type': 'modified',
                        'before': None,
                        'segments': [
                            {
                                'header': ['0', '0', '1', ''],
                                'lines': ['+hello world']
                            }
                        ],
                        'stats': {'added': 1, 'removed': 0}
                    }
                }
            },
            'commits': [
                {
                    'commitid': '5716de23b27020419d1a40dd93b469c041a1eeef',
                    'message': 'addd folder',
                    'timestamp': '2014-08-21T18:36:38.000Z',
                    'author': {'email': 'steve@stevepeak.net', 'name': 'stevepeak'}
                },
                {
                    'commitid': 'c739768fcac68144a3a6d82305b9c4106934d31a',
                    'message': "shhhh i'm batman!",
                    'timestamp': '2014-08-20T21:52:44.000Z',
                    'author': {'email': 'steve@stevepeak.net', 'name': 'stevepeak'}
                }
            ]
        }
        res = await valid_handler.get_compare(base, head)
        print(res)
        assert sorted(list(res.keys())) == sorted(list(expected_result.keys()))
        for key in res:
            assert res[key] == expected_result[key]
        assert res == expected_result

    @pytest.mark.asyncio
    async def test_get_repository(self, valid_handler, codecov_vcr):
        expected_result = {
            'owner': {'service_id': 126816, 'username': 'codecov'},
            'repo': {
                'branch': 'master',
                'language': None,
                'name': 'ci-repo',
                'private': False,
                'service_id': 187725
            }
        }
        res = await valid_handler.get_repository()
        assert res['repo'] == expected_result['repo']
        assert res == expected_result

    @pytest.mark.asyncio
    async def test_get_source_master(self, valid_handler, codecov_vcr):
        expected_result = {
            'commitid': None,
            'content': b"import unittest\nimport my_package\n\n\nclass TestMethods(unittest.TestCase):\n    def test_add(self):\n        self.assertEqual(my_package.add(10), 20)\n\nif __name__ == '__main__':\n    unittest.main()\n"
        }
        path, ref = 'tests.py', 'master'
        res = await valid_handler.get_source(path, ref)
        assert res == expected_result

    @pytest.mark.asyncio
    async def test_get_source_random_commit(self, valid_handler, codecov_vcr):
        expected_result = {
            'commitid': None,
            'content': b'hello world\n'
        }
        path, ref = 'folder/hello-world.txt', '5716de23'
        res = await valid_handler.get_source(path, ref)
        assert res == expected_result

    @pytest.mark.asyncio
    async def test_get_source_random_commit_not_found(self, valid_handler, codecov_vcr):
        path, ref = 'awesome/non_exising_file.py', '5716de23'
        with pytest.raises(TorngitObjectNotFoundError):
            await valid_handler.get_source(path, ref)

    @pytest.mark.asyncio
    async def test_list_repos(self, valid_handler, codecov_vcr):
        expected_result = [
            {
                'owner': {'service_id': 223023, 'username': 'morerunes'},
                'repo': {
                    'branch': 'master',
                    'fork': None,
                    'language': None,
                    'name': 'delectamentum-mud-server',
                    'private': False,
                    'service_id': 1384844
                }
            },
            {
                'owner': {'service_id': 126816, 'username': 'codecov'},
                'repo': {
                    'branch': 'master',
                    'fork': None,
                    'language': None,
                    'name': 'example-python',
                    'private': False,
                    'service_id': 580838}},
            {
                'owner': {'service_id': 126816, 'username': 'codecov'},
                'repo': {
                    'branch': 'master',
                    'fork': None,
                    'language': None,
                    'name': 'ci-private',
                    'private': True,
                    'service_id': 190307
                }
            },
            {
                'owner': {'service_id': 126816, 'username': 'codecov'},
                'repo': {
                    'branch': 'master',
                    'fork': None,
                    'language': None,
                    'name': 'ci-repo',
                    'private': False,
                    'service_id': 187725
                }
            }
        ]
        res = await valid_handler.list_repos()
        assert res == expected_result

    @pytest.mark.asyncio
    async def test_list_teams(self, valid_handler, codecov_vcr):
        expected_result = [
            {'id': 726800, 'name': 'delectamentum-mud', 'username': 'delectamentum-mud'}
        ]
        res = await valid_handler.list_teams()
        assert res == expected_result
