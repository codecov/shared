import random

import pytest

from torngit.exceptions import ObjectNotFoundException

from torngit.bitbucket import Bitbucket


@pytest.fixture
def valid_handler():
    return Bitbucket(
        repo=dict(name='example-python'),
        owner=dict(username='ThiagoCodecov'),
        oauth_consumer_token=dict(
            key='test51hdmhalc053rb',
            secret='testrgj6ezg5b4zc5z8t2rspg90rw6dp'
        ),
        token=dict(
            secret='testfl91v29591opmdfrxkzmu28qeixn',
            key='AgCFzqcDEXKjWZLPFD'
        )
    )


class TestBitbucketTestCase(object):

    @pytest.mark.asyncio
    async def test_post_comment(self, valid_handler, codecov_vcr):
        expected_result = {
            'anchor': None,
            'comment_id': 81514270,
            'comparespec': 'ThiagoCodecov/example-python:3017d534ab41\rb92edba44fdd',
            'content': 'Hello world',
            'content_rendered': '<p>Hello world</p>',
            'convert_markup': False,
            'deleted': False,
            'dest_rev': None,
            'display_name': 'Thiago Ramos',
            'filename': None,
            'filename_hash': None,
            'id': 81514270,
            'is_entity_author': True,
            'is_repo_owner': True,
            'is_spam': False,
            'line_from': None,
            'line_to': None,
            'parent_id': None,
            'pr_repo': {'owner': 'ThiagoCodecov', 'slug': 'example-python'},
            'pull_request_id': 1,
            'user_avatar_url': 'https://bitbucket.org/account/ThiagoCodecov/avatar/?ts=1541519035',
            'user_avatar_url_2x': 'https://bitbucket.org/account/ThiagoCodecov/avatar/64/?ts=1541519035',
            'username': 'ThiagoCodecov',
            'utc_created_on': '2018-11-06 16:04:23+00:00',
            'utc_last_updated': '2018-11-06 16:04:23+00:00',
        }
        res = await valid_handler.post_comment("1", "Hello world")
        assert res == expected_result

    @pytest.mark.asyncio
    async def test_edit_comment(self, valid_handler, codecov_vcr):
        res = await valid_handler.edit_comment("1", "81514270", "Hello world numbah 2")
        assert res is not None
        assert res['id'] == 81514270
        assert res['content'] == 'Hello world numbah 2'

    @pytest.mark.asyncio
    async def test_edit_comment_not_found(self, valid_handler, codecov_vcr):
        with pytest.raises(ObjectNotFoundException):
            await valid_handler.edit_comment("1", 113979999, "Hello world number 2")

    @pytest.mark.asyncio
    async def test_delete_comment(self, valid_handler, codecov_vcr):
        assert await valid_handler.delete_comment("1", "81514270") is True

    @pytest.mark.asyncio
    async def test_delete_comment_not_found(self, valid_handler, codecov_vcr):
        with pytest.raises(ObjectNotFoundException):
            await valid_handler.delete_comment("1", 113977999)

    @pytest.mark.asyncio
    async def test_find_pull_request_nothing_found(self, valid_handler, codecov_vcr):
        assert await valid_handler.find_pull_request('a' * 40, 'no-branch') is None

    @pytest.mark.asyncio
    async def test_get_pull_request_fail(self, valid_handler, codecov_vcr):
        with pytest.raises(ObjectNotFoundException):
            await valid_handler.get_pull_request("100")

    get_pull_request_test_data = [
        (
            '1',
            {
                'base': {
                    'branch': 'master',
                    'head': {
                        'branch': 'second-branch',
                        'commitid': '3017d534ab41e217bdf34d4c615fb355b0081f4b'
                    },
                    'number': '1',
                    'id': '1',
                    'state': 'open',
                    'title': 'Hahaa That is a PR',
                    'commitid': 'b92edba44fdd29fcc506317cc3ddeae1a723dd08'
                }
            }
        ),
    ]

    @pytest.mark.asyncio
    @pytest.mark.parametrize("a,b", get_pull_request_test_data)
    async def test_get_pull_request(self, valid_handler, a, b, codecov_vcr):
        res = await valid_handler.get_pull_request(a)
        assert res['base'] == b['base']
        assert res == b

    @pytest.mark.asyncio
    async def test_get_pull_request_commits(self, valid_handler, codecov_vcr):
        expected_result = ["3017d534ab41e217bdf34d4c615fb355b0081f4b"]
        res = await valid_handler.get_pull_request_commits("1")
        assert res == expected_result

    @pytest.mark.asyncio
    async def test_get_pull_requests(self, valid_handler, codecov_vcr):
        expected_result = [1]
        res = await valid_handler.get_pull_requests()
        assert res == expected_result

    @pytest.mark.asyncio
    async def test_get_commit(self, valid_handler, codecov_vcr):
        commit = await valid_handler.get_commit('6895b64')
        assert commit == {
            'author': {
                'id': None,
                'username': None,
                'email': 'jerrod@fundersclub.com',
                'name': 'Jerrod'
            },
            'message': "Adding 'include' term if multiple sources\n\nbased on a support ticket around multiple sources\r\n\r\nhttps://codecov.freshdesk.com/a/tickets/87",
            'parents': ['adb252173d2107fad86bcdcbc149884c2dd4c609'],
            'commitid': '6895b64',
            'timestamp': '2018-07-09T23:39:20+00:00'
        }

    @pytest.mark.asyncio
    async def test_get_commit_not_found(self, valid_handler, codecov_vcr):
        with pytest.raises(ObjectNotFoundException):
            await valid_handler.get_commit('none')

    @pytest.mark.asyncio
    async def test_get_commit_diff(self, valid_handler, codecov_vcr):
        expected_result = {
            'files': {
                'awesome/code_fib.py': {
                    'type': 'new',
                    'before': None,
                    'segments': [
                        {
                            'header': ['0', '0', '1', '4'],
                            'lines': [
                                '+def fib(n):', '+    if n <= 1:', '+        return 0', '+    return fib(n - 1) + fib(n - 2)'
                            ]
                        }
                    ],
                    'stats': {'added': 4, 'removed': 0}
                }
            }
        }
        res = await valid_handler.get_commit_diff('3017d53')
        assert res['files'] == expected_result['files']
        assert res == expected_result

    @pytest.mark.asyncio
    async def test_get_commit_statuses(self, valid_handler, codecov_vcr):
        res = await valid_handler.get_commit_statuses('3017d53')
        assert res == 'success'

    @pytest.mark.asyncio
    async def test_set_commit_status(self, valid_handler, codecov_vcr):
        target_url = 'https://localhost:50036/gitlab/codecov/ci-repo?ref=ad798926730aad14aadf72281204bdb85734fe67'
        expected_result = {
            'key': 'codecov-context',
            'description': 'aaaaaaaaaa',
            'repository': {
                'links': {
                    'self': {
                        'href': 'https://bitbucket.org/!api/2.0/repositories/ThiagoCodecov/example-python'
                    },
                    'html': {
                        'href': 'https://bitbucket.org/ThiagoCodecov/example-python'
                    },
                    'avatar': {
                            'href': 'https://bytebucket.org/ravatar/%7Ba8c50527-2c3a-480e-afe1-7700e2b00074%7D?ts=default'
                    }
                },
                'type': 'repository', 'name': 'example-python',
                'full_name': 'ThiagoCodecov/example-python',
                'uuid': '{a8c50527-2c3a-480e-afe1-7700e2b00074}'
            },
            'url': 'https://localhost:50036/gitlab/codecov/ci-repo?ref=ad798926730aad14aadf72281204bdb85734fe67',
            'links': {
                'commit': {
                    'href': 'https://bitbucket.org/!api/2.0/repositories/ThiagoCodecov/example-python/commit/3017d534ab41e217bdf34d4c615fb355b0081f4b'
                },
                'self': {
                    'href': 'https://bitbucket.org/!api/2.0/repositories/ThiagoCodecov/example-python/commit/3017d534ab41e217bdf34d4c615fb355b0081f4b/statuses/build/codecov-context'
                }
            }, 'refname': None, 'state': 'SUCCESSFUL', 'created_on': '2018-11-07T14:25:50.103547+00:00',
            'commit': {
                'hash': '3017d534ab41e217bdf34d4c615fb355b0081f4b', 'type': 'commit',
                'links': {
                    'self': {
                        'href': 'https://bitbucket.org/!api/2.0/repositories/ThiagoCodecov/example-python/commit/3017d534ab41e217bdf34d4c615fb355b0081f4b'
                    },
                    'html': {
                        'href': 'https://bitbucket.org/ThiagoCodecov/example-python/commits/3017d534ab41e217bdf34d4c615fb355b0081f4b'
                    }
                }
            },
            'updated_on': '2018-11-07T14:25:50.103583+00:00',
            'type': 'build', 'name': 'Context Coverage'
        }
        res = await valid_handler.set_commit_status(
            '3017d53',
            'success',
            'context',
            'aaaaaaaaaa',
            target_url
        )
        print(res)
        assert res == expected_result

    @pytest.mark.asyncio
    async def test_get_branches(self, valid_handler, codecov_vcr):
        branches = sorted(await valid_handler.get_branches())
        assert list(map(lambda a: a[0], branches)) == ['example', 'future', 'master', 'second-branch']

    @pytest.mark.asyncio
    async def test_post_webhook(self, valid_handler, codecov_vcr):
        url = 'http://requestbin.net/r/1ecyaj51'
        events = [
            "repo:push",
            "issue:created",
        ]
        name, secret = 'a', 'd'
        expected_result = {
            'read_only': None,
            'description': 'a',
            'links': {
                'self': {'href': 'https://bitbucket.org/!api/2.0/repositories/ThiagoCodecov/example-python/hooks/%7B4742f092-8397-4677-8876-5e9a06f10f98%7D'}
            },
            'url': 'http://requestbin.net/r/1ecyaj51',
            'created_at': '2018-11-07T14:45:47.900077Z',
            'skip_cert_verification': False,
            'source': None,
            'history_enabled': False,
            'active': True,
            'subject': {
                'links': {
                    'self': {
                        'href': 'https://bitbucket.org/!api/2.0/repositories/ThiagoCodecov/example-python'
                    },
                    'html': {'href': 'https://bitbucket.org/ThiagoCodecov/example-python'},
                    'avatar': {'href': 'https://bytebucket.org/ravatar/%7Ba8c50527-2c3a-480e-afe1-7700e2b00074%7D?ts=default'}
                },
                'type': 'repository',
                'name': 'example-python',
                'full_name': 'ThiagoCodecov/example-python',
                'uuid': '{a8c50527-2c3a-480e-afe1-7700e2b00074}'
            },
            'type': 'webhook_subscription',
            'events': [
                'issue:created',
                'repo:push'
            ],
            'uuid': '{4742f092-8397-4677-8876-5e9a06f10f98}',
            'id': '4742f092-8397-4677-8876-5e9a06f10f98'
        }
        res = await valid_handler.post_webhook(name, url, events, secret)
        print(res)
        assert res == expected_result

    @pytest.mark.asyncio
    async def test_edit_webhook(self, valid_handler, codecov_vcr):
        url = 'http://requestbin.net/r/1ecyaj51'
        events = [
            "issue:updated"
        ]
        new_name, secret = 'new_name', 'new_secret'
        expected_result = {
            'read_only': None,
            'description': 'new_name',
            'links': {
                'self': {'href': 'https://bitbucket.org/!api/2.0/repositories/ThiagoCodecov/example-python/hooks/%7B4742f092-8397-4677-8876-5e9a06f10f98%7D'}
            },
            'url': 'http://requestbin.net/r/1ecyaj51',
            'created_at': '2018-11-07T14:45:47.900077Z',
            'skip_cert_verification': False,
            'source': None,
            'history_enabled': False,
            'active': True,
            'subject': {
                'links': {
                    'self': {
                        'href': 'https://bitbucket.org/!api/2.0/repositories/ThiagoCodecov/example-python'
                    },
                    'html': {'href': 'https://bitbucket.org/ThiagoCodecov/example-python'},
                    'avatar': {'href': 'https://bytebucket.org/ravatar/%7Ba8c50527-2c3a-480e-afe1-7700e2b00074%7D?ts=default'}
                },
                'type': 'repository',
                'name': 'example-python',
                'full_name': 'ThiagoCodecov/example-python',
                'uuid': '{a8c50527-2c3a-480e-afe1-7700e2b00074}'
            },
            'type': 'webhook_subscription',
            'events': ['issue:updated'],
            'uuid': '{4742f092-8397-4677-8876-5e9a06f10f98}',
            'id': '4742f092-8397-4677-8876-5e9a06f10f98'
        }
        res = await valid_handler.edit_webhook(
            '4742f092-8397-4677-8876-5e9a06f10f98', new_name, url, events, secret)
        assert res == expected_result

    @pytest.mark.asyncio
    async def test_delete_webhook(self, valid_handler, codecov_vcr):
        res = await valid_handler.delete_webhook('4742f092-8397-4677-8876-5e9a06f10f98')
        assert res is True

    @pytest.mark.asyncio
    async def test_delete_webhook_not_found(self, valid_handler, codecov_vcr):
        with pytest.raises(ObjectNotFoundException):
            await valid_handler.delete_webhook('4742f011-8397-aa77-8876-5e9a06f10f98')

    @pytest.mark.asyncio
    async def test_get_authenticated(self, valid_handler, codecov_vcr):
        res = await valid_handler.get_authenticated()
        assert res == (True, False)

    @pytest.mark.asyncio
    async def test_get_compare(self, valid_handler, codecov_vcr):
        base, head = '6ae5f17', 'b92edba'
        expected_result = {
            'diff': {
                'files': {
                    'README.rst': {
                        'type': 'modified',
                        'before': None,
                        'segments': [
                            {
                                'header': ['12', '', '12', '2'],
                                'lines': [
                                    '-Main website: `Codecov <https://codecov.io/>`_.', '+',
                                    '+website: `Codecov <https://codecov.io/>`_.'
                                ]
                            },
                            {
                                'header': ['49', '', '50', ''],
                                'lines': [
                                    '-We highly suggest adding `source` to your ``.coveragerc`` which solves a number of issues collecting coverage.',
                                    '+We highly suggest adding ``source`` to your ``.coveragerc``, which solves a number of issues collecting coverage.'
                                ]
                            },
                            {
                                'header': ['54', '0', '56', '7'],
                                'lines': [
                                    '+   ',
                                    '+If there are multiple sources, you instead should add ``include`` to your ``.coveragerc``', '+',
                                    '+.. code-block:: ini', '+', '+   [run]', '+   include=your_package_name/*'
                                ]
                            },
                            {
                                'header': ['153', '2', '161', ''],
                                'lines': [
                                    '-We are happy to help if you have any questions. Please contact email our Support at [support@codecov.io](mailto:support@codecov.io)',
                                    '-', '+We are happy to help if you have any questions. Please contact email our Support at `support@codecov.io <mailto:support@codecov.io>`_.'
                                ]
                            }
                        ],
                        'stats': {'added': 11, 'removed': 4}
                    }
                }
            },
            'commits': [{'commitid': 'b92edba'}, {'commitid': '6ae5f17'}]
        }
        res = await valid_handler.get_compare(base, head)
        assert sorted(list(res.keys())) == sorted(list(expected_result.keys()))
        assert res == expected_result

    @pytest.mark.asyncio
    async def test_get_compare_same_commit(self, valid_handler, codecov_vcr):
        base, head = '6ae5f17', '6ae5f17'
        expected_result = {
            'diff': None,
            'commits': [{'commitid': '6ae5f17'}, {'commitid': '6ae5f17'}]
        }
        res = await valid_handler.get_compare(base, head)
        assert sorted(list(res.keys())) == sorted(list(expected_result.keys()))
        assert res == expected_result

    @pytest.mark.asyncio
    async def test_get_repository(self, valid_handler, codecov_vcr):
        expected_result = {
            'owner': {'service_id': '9a01f37b-b1b2-40c5-8c5e-1a39f4b5e645', 'username': 'ThiagoCodecov'},
            'repo': {
                'branch': 'master',
                'language': None,
                'name': 'example-python',
                'private': True,
                'service_id': 'a8c50527-2c3a-480e-afe1-7700e2b00074'
            }
        }
        res = await valid_handler.get_repository()
        assert res['repo'] == expected_result['repo']
        assert res == expected_result

    @pytest.mark.asyncio
    async def test_get_source_master(self, valid_handler, codecov_vcr):
        expected_result = {
            'commitid': 'b92edba44fdd',
            'content': 'import unittest\n\nimport awesome\n\n\nclass TestMethods(unittest.TestCase):\n    def test_add(self):\n        self.assertEqual(awesome.smile(), ":)")\n\n\nif __name__ == \'__main__\':\n    unittest.main()\n'
        }
        path, ref = 'tests.py', 'master'
        res = await valid_handler.get_source(path, ref)
        print(res)
        assert res == expected_result

    @pytest.mark.asyncio
    async def test_get_source_random_commit(self, valid_handler, codecov_vcr):
        expected_result = {
            'commitid': '96492d409fc8',
            'content': 'def smile():\n    return ":)"\n\ndef frown():\n    return ":("\n'
        }
        path, ref = 'awesome/__init__.py', '96492d409fc86aa7ae31b214dfe6b08ae860458a'
        res = await valid_handler.get_source(path, ref)
        assert res == expected_result

    @pytest.mark.asyncio
    async def test_list_repos(self, valid_handler, codecov_vcr):
        expected_result = [
            {
                'owner': {
                    'service_id': '9a01f37b-b1b2-40c5-8c5e-1a39f4b5e645',
                    'username': 'ThiagoCodecov'
                },
                'repo': {
                    'service_id': 'a8c50527-2c3a-480e-afe1-7700e2b00074',
                    'name': 'example-python',
                    'language': None,
                    'private': True,
                    'branch': 'master',
                    'fork': None
                }
            }
        ]

        res = await valid_handler.list_repos('ThiagoCodecov')
        assert res == expected_result

    @pytest.mark.asyncio
    async def test_list_teams(self, valid_handler, codecov_vcr):
        expected_result = []
        res = await valid_handler.list_teams()
        assert res == expected_result
