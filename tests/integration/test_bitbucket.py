import pytest
import vcr

from shared.torngit.bitbucket import Bitbucket
from shared.torngit.enums import Endpoints
from shared.torngit.exceptions import TorngitObjectNotFoundError


@pytest.fixture
def valid_handler():
    return Bitbucket(
        repo=dict(name="example-python"),
        owner=dict(
            username="ThiagoCodecov", service_id="9a01f37b-b1b2-40c5-8c5e-1a39f4b5e645"
        ),
        oauth_consumer_token=dict(
            key="arubajamaicaohiwan", secret="natakeyoubermudabahamacomeonpret"
        ),
        token=dict(secret="testpnilpfmyehw45pa7rvtkvtm7bhcx", key="testss3hxhcfqf1h6g"),
    )


@pytest.fixture
def valid_codecov_handler():
    return Bitbucket(
        repo=dict(name="private"),
        owner=dict(username="codecov"),
        oauth_consumer_token=dict(
            key="arubajamaicaohiwan", secret="natakeyoubermudabahamacomeonpret"
        ),
        token=dict(secret="KeyLargoMontegobabywhydontwego", key="waydowntokokomo"),
    )


class TestBitbucketTestCase(object):
    @pytest.mark.asyncio
    async def test_get_best_effort_branches(self, valid_handler, codecov_vcr):
        branches = await valid_handler.get_best_effort_branches("6a45b83")
        assert branches == []

    @pytest.mark.asyncio
    async def test_post_comment(self, valid_handler, codecov_vcr):
        expected_result = {
            "deleted": False,
            "id": 114320127,
            "content": {
                "html": "<p>Hello world</p>",
                "markup": "markdown",
                "raw": "Hello world",
                "type": "rendered",
            },
            "created_on": "2019-08-24T07:22:19.710114+00:00",
            "links": {
                "html": {
                    "href": "https://bitbucket.org/ThiagoCodecov/example-python/pull-requests/1/_/diff#comment-114320127"
                },
                "self": {
                    "href": "https://bitbucket.org/!api/2.0/repositories/ThiagoCodecov/example-python/pullrequests/1/comments/114320127"
                },
            },
            "pullrequest": {
                "id": 1,
                "links": {
                    "html": {
                        "href": "https://bitbucket.org/ThiagoCodecov/example-python/pull-requests/1"
                    },
                    "self": {
                        "href": "https://bitbucket.org/!api/2.0/repositories/ThiagoCodecov/example-python/pullrequests/1"
                    },
                },
                "title": "Hahaa That is a PR",
                "type": "pullrequest",
            },
            "type": "pullrequest_comment",
            "updated_on": "2019-08-24T07:22:19.719805+00:00",
            "user": {
                "account_id": "5bce04c759d0e84f8c7555e9",
                "display_name": "Thiago Ramos",
                "links": {
                    "avatar": {
                        "href": "https://avatar-management--avatars.us-west-2.prod.public.atl-paas.net/initials/TR-6.png"
                    },
                    "html": {
                        "href": "https://bitbucket.org/%7B9a01f37b-b1b2-40c5-8c5e-1a39f4b5e645%7D/"
                    },
                    "self": {
                        "href": "https://bitbucket.org/!api/2.0/users/%7B9a01f37b-b1b2-40c5-8c5e-1a39f4b5e645%7D"
                    },
                },
                "nickname": "thiago",
                "type": "user",
                "uuid": "{9a01f37b-b1b2-40c5-8c5e-1a39f4b5e645}",
            },
        }
        res = await valid_handler.post_comment("1", "Hello world")
        assert res == expected_result

    @pytest.mark.asyncio
    async def test_edit_comment(self, valid_handler, codecov_vcr):
        res = await valid_handler.edit_comment("1", "114320127", "Hello world numbah 2")
        assert res is not None
        assert res["id"] == 114320127
        assert res["content"]["raw"] == "Hello world numbah 2"

    @pytest.mark.asyncio
    async def test_edit_comment_not_found(self, valid_handler, codecov_vcr):
        with pytest.raises(TorngitObjectNotFoundError):
            await valid_handler.edit_comment("1", 113979999, "Hello world number 2")

    @pytest.mark.asyncio
    async def test_delete_comment(self, valid_handler, codecov_vcr):
        assert await valid_handler.delete_comment("1", "107383471") is True

    @pytest.mark.asyncio
    async def test_delete_comment_not_found(self, valid_handler, codecov_vcr):
        with pytest.raises(TorngitObjectNotFoundError):
            await valid_handler.delete_comment("1", 113977999)

    @pytest.mark.asyncio
    async def test_find_pull_request_nothing_found(self, valid_handler, codecov_vcr):
        assert await valid_handler.find_pull_request("a" * 40, "no-branch") is None

    @pytest.mark.asyncio
    async def test_get_pull_request_fail(self, valid_handler, codecov_vcr):
        with pytest.raises(TorngitObjectNotFoundError):
            await valid_handler.get_pull_request("100")

    get_pull_request_test_data = [
        (
            "1",
            {
                "base": {
                    "branch": "main",
                    "commitid": "b92edba44fdd29fcc506317cc3ddeae1a723dd08",
                },
                "head": {
                    "branch": "second-branch",
                    "commitid": "3017d534ab41e217bdf34d4c615fb355b0081f4b",
                },
                "number": "1",
                "id": "1",
                "state": "open",
                "title": "Hahaa That is a PR",
                "author": {
                    "id": "9a01f37b-b1b2-40c5-8c5e-1a39f4b5e645",
                    "username": "ThiagoCodecov",
                },
            },
        )
    ]

    @pytest.mark.asyncio
    @pytest.mark.parametrize("a,b", get_pull_request_test_data)
    async def test_get_pull_request(self, valid_handler, a, b, codecov_vcr):
        res = await valid_handler.get_pull_request(a)
        assert res["base"] == b["base"]
        assert res == b

    @pytest.mark.asyncio
    async def test_get_pull_request_commits(self, valid_handler, codecov_vcr):
        expected_result = ["3017d534ab41e217bdf34d4c615fb355b0081f4b"]
        res = await valid_handler.get_pull_request_commits("1")
        assert res == expected_result

    @pytest.mark.asyncio
    async def test_get_pull_request_commits_multiple_pages(
        self, valid_handler, codecov_vcr
    ):
        expected_result = [
            "f8a26b4c1bf8eef0bc3aeeb0b23f74f4b96a7d04",
            "d3bedda462a79fafe4f5dfdb0ecf710f558e6aab",
            "bd666be433ce4123ab0674fc8eb86708d340c31b",
            "c80b02c4b65d141f0274ebb13e2a88f22a31820c",
            "b3fe71aeb1a405219f4bf58d44ba9a0057072d06",
            "2909d0fae30c1d3e628cab1f549e29e1da7b385d",
            "3fe51078bb5f6000617d71e32cfde4ebed6f2052",
            "974bce36e097868d6eb087656f929dd698d0507e",
            "3b2aa7b423369c766173121e8a8bfa2d225ee235",
            "f1b9dc07dcd5301c215824d1884816435cf269ea",
            "266e6b98f88847c8c4b6e8cf38cf5397266211d3",
            "3017d534ab41e217bdf34d4c615fb355b0081f4b",
        ]
        res = await valid_handler.get_pull_request_commits("1")
        assert res == expected_result

    @pytest.mark.asyncio
    async def test_get_pull_requests(self, valid_handler, codecov_vcr):
        expected_result = [1]
        res = await valid_handler.get_pull_requests()
        assert res == expected_result

    @pytest.mark.asyncio
    async def test_get_commit(self, valid_codecov_handler, codecov_vcr):
        commit = await valid_codecov_handler.get_commit("6a45b83")
        assert commit == {
            "commitid": "6a45b83",
            "timestamp": "2015-02-27T03:44:32+00:00",
            "message": """wip\n""",
            "parents": ["0028015f7fa260f5fd68f78c0deffc15183d955e"],
            "author": {
                "username": "stevepeak",
                "id": "test6y9pl15lzivhmkgsk67k10x53n04i85o",
                "name": "stevepeak",
                "email": "steve@stevepeak.net",
            },
        }

    @pytest.mark.asyncio
    async def test_get_commit_no_uuid(self, valid_codecov_handler, codecov_vcr):
        commit = await valid_codecov_handler.get_commit("6a45b83")
        assert commit == {
            "commitid": "6a45b83",
            "timestamp": "2015-02-27T03:44:32+00:00",
            "message": """wip\n""",
            "parents": ["0028015f7fa260f5fd68f78c0deffc15183d955e"],
            "author": {
                "username": "stevepeak",
                "id": "test6y9pl15lzivhmkgsk67k10x53n04i85o",
                "name": "stevepeak",
                "email": "steve@stevepeak.net",
            },
        }

    @pytest.mark.asyncio
    async def test_get_commit_not_found(self, valid_handler, codecov_vcr):
        with pytest.raises(TorngitObjectNotFoundError):
            await valid_handler.get_commit("none")

    @pytest.mark.asyncio
    async def test_get_commit_diff(self, valid_handler, codecov_vcr):
        expected_result = {
            "files": {
                "awesome/code_fib.py": {
                    "type": "new",
                    "before": None,
                    "segments": [
                        {
                            "header": ["0", "0", "1", "4"],
                            "lines": [
                                "+def fib(n):",
                                "+    if n <= 1:",
                                "+        return 0",
                                "+    return fib(n - 1) + fib(n - 2)",
                            ],
                        }
                    ],
                    "stats": {"added": 4, "removed": 0},
                }
            }
        }
        res = await valid_handler.get_commit_diff("3017d53")
        assert res["files"] == expected_result["files"]
        assert res == expected_result

    @pytest.mark.asyncio
    async def test_get_commit_statuses(self, valid_handler, codecov_vcr):
        res = await valid_handler.get_commit_statuses("3017d53")
        assert res == "success"

    @pytest.mark.asyncio
    async def test_get_is_admin(self, valid_handler, codecov_vcr):
        valid_handler.data = dict(
            owner=dict(
                username="ThiagoRRamosworkspace",
                service_id="727d78e8-7431-4532-9519-1e5fe2b61d4b",
            )
        )
        user = dict(service_id="9a01f37b-b1b2-40c5-8c5e-1a39f4b5e645")
        res = await valid_handler.get_is_admin(user)
        assert res is True

    @pytest.mark.asyncio
    async def test_get_is_admin_not_admin(self, valid_handler, codecov_vcr):
        valid_handler.data = dict(
            owner=dict(
                username="thiagorramostestnumbar3",
                service_id="d7c73e87-90ab-450f-bb5f-39e6a5870456",
            )
        )
        user = dict(service_id="9a01f37b-b1b2-40c5-8c5e-1a39f4b5e645")
        res = await valid_handler.get_is_admin(user)
        assert res is False

    @pytest.mark.asyncio
    async def test_set_commit_status(self, valid_handler, codecov_vcr):
        target_url = "https://localhost:50036/gitlab/codecov/ci-repo?ref=ad798926730aad14aadf72281204bdb85734fe67"
        expected_result = {
            "key": "codecov-context",
            "description": "aaaaaaaaaa",
            "repository": {
                "links": {
                    "self": {
                        "href": "https://bitbucket.org/!api/2.0/repositories/ThiagoCodecov/example-python"
                    },
                    "html": {
                        "href": "https://bitbucket.org/ThiagoCodecov/example-python"
                    },
                    "avatar": {
                        "href": "https://bytebucket.org/ravatar/%7Ba8c50527-2c3a-480e-afe1-7700e2b00074%7D?ts=default"
                    },
                },
                "type": "repository",
                "name": "example-python",
                "full_name": "ThiagoCodecov/example-python",
                "uuid": "{a8c50527-2c3a-480e-afe1-7700e2b00074}",
            },
            "url": "https://localhost:50036/gitlab/codecov/ci-repo?ref=ad798926730aad14aadf72281204bdb85734fe67",
            "links": {
                "commit": {
                    "href": "https://bitbucket.org/!api/2.0/repositories/ThiagoCodecov/example-python/commit/3017d534ab41e217bdf34d4c615fb355b0081f4b"
                },
                "self": {
                    "href": "https://bitbucket.org/!api/2.0/repositories/ThiagoCodecov/example-python/commit/3017d534ab41e217bdf34d4c615fb355b0081f4b/statuses/build/codecov-context"
                },
            },
            "refname": None,
            "state": "SUCCESSFUL",
            "created_on": "2018-11-07T14:25:50.103547+00:00",
            "commit": {
                "hash": "3017d534ab41e217bdf34d4c615fb355b0081f4b",
                "type": "commit",
                "links": {
                    "self": {
                        "href": "https://bitbucket.org/!api/2.0/repositories/ThiagoCodecov/example-python/commit/3017d534ab41e217bdf34d4c615fb355b0081f4b"
                    },
                    "html": {
                        "href": "https://bitbucket.org/ThiagoCodecov/example-python/commits/3017d534ab41e217bdf34d4c615fb355b0081f4b"
                    },
                },
            },
            "updated_on": "2018-11-07T14:25:50.103583+00:00",
            "type": "build",
            "name": "Context Coverage",
        }
        res = await valid_handler.set_commit_status(
            "3017d53", "success", "context", "aaaaaaaaaa", target_url
        )
        assert res == expected_result

    @pytest.mark.asyncio
    async def test_get_branches(self, valid_handler, codecov_vcr):
        branches = sorted(await valid_handler.get_branches())
        assert list(map(lambda a: a[0], branches)) == [
            "example",
            "f/new-branch",
            "future",
            "main",
            "second-branch",
        ]

    @pytest.mark.asyncio
    async def test_post_webhook(self, valid_handler, codecov_vcr):
        url = "http://requestbin.net/r/1ecyaj51"
        events = ["repo:push", "issue:created"]
        name, secret = "a", "d"
        expected_result = {
            "read_only": None,
            "description": "a",
            "links": {
                "self": {
                    "href": "https://bitbucket.org/!api/2.0/repositories/ThiagoCodecov/example-python/hooks/%7B4742f092-8397-4677-8876-5e9a06f10f98%7D"
                }
            },
            "url": "http://requestbin.net/r/1ecyaj51",
            "created_at": "2018-11-07T14:45:47.900077Z",
            "skip_cert_verification": False,
            "source": None,
            "history_enabled": False,
            "active": True,
            "subject": {
                "links": {
                    "self": {
                        "href": "https://bitbucket.org/!api/2.0/repositories/ThiagoCodecov/example-python"
                    },
                    "html": {
                        "href": "https://bitbucket.org/ThiagoCodecov/example-python"
                    },
                    "avatar": {
                        "href": "https://bytebucket.org/ravatar/%7Ba8c50527-2c3a-480e-afe1-7700e2b00074%7D?ts=default"
                    },
                },
                "type": "repository",
                "name": "example-python",
                "full_name": "ThiagoCodecov/example-python",
                "uuid": "{a8c50527-2c3a-480e-afe1-7700e2b00074}",
            },
            "type": "webhook_subscription",
            "events": ["issue:created", "repo:push"],
            "uuid": "{4742f092-8397-4677-8876-5e9a06f10f98}",
            "id": "4742f092-8397-4677-8876-5e9a06f10f98",
        }
        res = await valid_handler.post_webhook(name, url, events, secret)
        assert res == expected_result

    @pytest.mark.asyncio
    async def test_edit_webhook(self, valid_handler, codecov_vcr):
        url = "http://requestbin.net/r/1ecyaj51"
        events = ["issue:updated"]
        new_name, secret = "new_name", "new_secret"
        expected_result = {
            "read_only": None,
            "description": "new_name",
            "links": {
                "self": {
                    "href": "https://bitbucket.org/!api/2.0/repositories/ThiagoCodecov/example-python/hooks/%7B4742f092-8397-4677-8876-5e9a06f10f98%7D"
                }
            },
            "url": "http://requestbin.net/r/1ecyaj51",
            "created_at": "2018-11-07T14:45:47.900077Z",
            "skip_cert_verification": False,
            "source": None,
            "history_enabled": False,
            "active": True,
            "subject": {
                "links": {
                    "self": {
                        "href": "https://bitbucket.org/!api/2.0/repositories/ThiagoCodecov/example-python"
                    },
                    "html": {
                        "href": "https://bitbucket.org/ThiagoCodecov/example-python"
                    },
                    "avatar": {
                        "href": "https://bytebucket.org/ravatar/%7Ba8c50527-2c3a-480e-afe1-7700e2b00074%7D?ts=default"
                    },
                },
                "type": "repository",
                "name": "example-python",
                "full_name": "ThiagoCodecov/example-python",
                "uuid": "{a8c50527-2c3a-480e-afe1-7700e2b00074}",
            },
            "type": "webhook_subscription",
            "events": ["issue:updated"],
            "uuid": "{4742f092-8397-4677-8876-5e9a06f10f98}",
            "id": "4742f092-8397-4677-8876-5e9a06f10f98",
        }
        res = await valid_handler.edit_webhook(
            "4742f092-8397-4677-8876-5e9a06f10f98", new_name, url, events, secret
        )
        assert res == expected_result

    @pytest.mark.asyncio
    async def test_delete_webhook(self, valid_handler, codecov_vcr):
        res = await valid_handler.delete_webhook("4742f092-8397-4677-8876-5e9a06f10f98")
        assert res is True

    @pytest.mark.asyncio
    async def test_delete_webhook_not_found(self, valid_handler, codecov_vcr):
        with pytest.raises(TorngitObjectNotFoundError):
            await valid_handler.delete_webhook("4742f011-8397-aa77-8876-5e9a06f10f98")

    @pytest.mark.asyncio
    async def test_get_authenticated(self, valid_handler, codecov_vcr):
        res = await valid_handler.get_authenticated()
        # This needs to be True/True because ThiagoCodecov owns the repo ThiagoCodecov/example-python
        assert res == (True, True)

    @pytest.mark.asyncio
    async def test_get_authenticated_no_edit_permission(
        self, valid_handler, codecov_vcr
    ):
        valid_handler.data["repo"] = {"name": "stash-example-plugin"}
        valid_handler.data["owner"]["username"] = "atlassian"
        res = await valid_handler.get_authenticated()
        # This needs to be True/False because ThiagoCodecov has nothing to do with this repo
        assert res == (True, False)

    @pytest.mark.asyncio
    async def test_get_compare(self, valid_handler, codecov_vcr):
        base, head = "6ae5f17", "b92edba"
        expected_result = {
            "diff": {
                "files": {
                    "README.rst": {
                        "type": "modified",
                        "before": None,
                        "segments": [
                            {
                                "header": ["11", "3", "11", "4"],
                                "lines": [
                                    " ",
                                    "-Main website: `Codecov <https://codecov.io/>`_.",
                                    "+",
                                    "+website: `Codecov <https://codecov.io/>`_.",
                                    " ",
                                ],
                            },
                            {
                                "header": ["48", "3", "49", "3"],
                                "lines": [
                                    " ",
                                    "-We highly suggest adding `source` to your ``.coveragerc`` which solves a number of issues collecting coverage.",
                                    "+We highly suggest adding ``source`` to your ``.coveragerc``, which solves a number of issues collecting coverage.",
                                    " ",
                                ],
                            },
                            {
                                "header": ["54", "2", "55", "9"],
                                "lines": [
                                    "    source=your_package_name",
                                    "+   ",
                                    "+If there are multiple sources, you instead should add ``include`` to your ``.coveragerc``",
                                    "+",
                                    "+.. code-block:: ini",
                                    "+",
                                    "+   [run]",
                                    "+   include=your_package_name/*",
                                    " ",
                                ],
                            },
                            {
                                "header": ["152", "3", "160", "2"],
                                "lines": [
                                    " ",
                                    "-We are happy to help if you have any questions. Please contact email our Support at [support@codecov.io](mailto:support@codecov.io)",
                                    "-",
                                    "+We are happy to help if you have any questions. Please contact email our Support at `support@codecov.io <mailto:support@codecov.io>`_.",
                                ],
                            },
                        ],
                        "stats": {"added": 11, "removed": 4},
                    }
                }
            },
            "commits": [{"commitid": "b92edba"}, {"commitid": "6ae5f17"}],
        }
        res = await valid_handler.get_compare(base, head)
        print(res)
        assert sorted(list(res.keys())) == sorted(list(expected_result.keys()))
        assert res == expected_result

    @pytest.mark.asyncio
    async def test_get_compare_same_commit(self, valid_handler, codecov_vcr):
        base, head = "6ae5f17", "6ae5f17"
        expected_result = {
            "diff": None,
            "commits": [{"commitid": "6ae5f17"}, {"commitid": "6ae5f17"}],
        }
        res = await valid_handler.get_compare(base, head)
        assert sorted(list(res.keys())) == sorted(list(expected_result.keys()))
        assert res == expected_result

    @pytest.mark.asyncio
    async def test_get_repository(self, valid_handler, codecov_vcr):
        expected_result = {
            "owner": {
                "service_id": "9a01f37b-b1b2-40c5-8c5e-1a39f4b5e645",
                "username": "ThiagoCodecov",
            },
            "repo": {
                "branch": "main",
                "language": None,
                "name": "example-python",
                "private": True,
                "service_id": "a8c50527-2c3a-480e-afe1-7700e2b00074",
            },
        }
        res = await valid_handler.get_repository()
        assert res["repo"] == expected_result["repo"]
        assert res == expected_result

    @pytest.mark.asyncio
    async def test_get_source_master(self, valid_handler, codecov_vcr):
        expected_result = {
            "commitid": None,
            "content": b"from kaploft import smile, fib\n\n\ndef test_something():\n    assert smile() == ':)'\n\n\ndef test_fib():\n    assert fib(1) == 1\n\n\ndef test_fib_second():\n    assert fib(3) == 3\n",
        }
        path, ref = "tests/test_k.py", "master"
        res = await valid_handler.get_source(path, ref)
        assert res == expected_result

    @pytest.mark.asyncio
    async def test_get_source_random_commit(self, valid_handler, codecov_vcr):
        expected_result = {
            "commitid": None,
            "content": b'def smile():\n    return ":)"\n\ndef frown():\n    return ":("\n',
        }
        path, ref = "awesome/__init__.py", "96492d409fc86aa7ae31b214dfe6b08ae860458a"
        res = await valid_handler.get_source(path, ref)
        assert res == expected_result

    @pytest.mark.asyncio
    async def test_get_source_random_commit_not_found(self, valid_handler, codecov_vcr):
        path, ref = (
            "awesome/non_exising_file.py",
            "96492d409fc86aa7ae31b214dfe6b08ae860458a",
        )
        with pytest.raises(TorngitObjectNotFoundError):
            await valid_handler.get_source(path, ref)

    @pytest.mark.asyncio
    async def test_list_repos(self, valid_handler, codecov_vcr):
        expected_result = [
            {
                "repo": {
                    "name": "ci-repo",
                    "language": None,
                    "branch": "main",
                    "service_id": "a980e378-088f-48a8-9850-98923f497546",
                    "private": False,
                },
                "owner": {
                    "username": "codecov",
                    "service_id": "6ef29b63-aaaa-aaaa-aaaa-aaaa03f5cd49",
                },
            },
            {
                "repo": {
                    "name": "private",
                    "language": "python",
                    "branch": "main",
                    "service_id": "3edf54ab-cfe4-4049-aa70-5eb9f69f60d4",
                    "private": True,
                },
                "owner": {
                    "username": "codecov",
                    "service_id": "6ef29b63-aaaa-aaaa-aaaa-aaaa03f5cd49",
                },
            },
            {
                "repo": {
                    "name": "coverage.py",
                    "language": "python",
                    "branch": "main",
                    "service_id": "d08f4587-489f-4b55-abad-3d4f396d9862",
                    "private": False,
                },
                "owner": {
                    "username": "codecov",
                    "service_id": "6ef29b63-aaaa-aaaa-aaaa-aaaa03f5cd49",
                },
            },
            {
                "repo": {
                    "name": "integration-test-repo",
                    "language": "python",
                    "branch": "main",
                    "service_id": "4fab7a33-92dd-450b-8d12-ea1ab7816300",
                    "private": True,
                },
                "owner": {
                    "username": "codecov",
                    "service_id": "6ef29b63-aaaa-aaaa-aaaa-aaaa03f5cd49",
                },
            },
            {
                "repo": {
                    "name": "test-bb-integration-public",
                    "language": None,
                    "branch": "main",
                    "service_id": "2e219352-777c-4e2b-9a16-71211fbd4d93",
                    "private": False,
                },
                "owner": {
                    "username": "codecov",
                    "service_id": "6ef29b63-aaaa-aaaa-aaaa-aaaa03f5cd49",
                },
            },
        ]

        res = await valid_handler.list_repos("codecov")
        assert sorted(res, key=lambda x: x["repo"]["service_id"]) == sorted(
            expected_result, key=lambda x: x["repo"]["service_id"]
        )

    @pytest.mark.asyncio
    @vcr.use_cassette(
        "tests/integration/cassetes/test_bitbucket/TestBitbucketTestCase/test_list_repos.yaml",
        record_mode="none",
        filter_headers=["authorization"],
        match_on=["method", "scheme", "host", "port", "path", "query"],
        filter_query_parameters=["oauth_nonce", "oauth_timestamp", "oauth_signature"],
    )
    async def test_list_repos_generator(self, valid_handler, codecov_vcr):
        expected_result = [
            {
                "repo": {
                    "name": "ci-repo",
                    "language": None,
                    "branch": "main",
                    "service_id": "a980e378-088f-48a8-9850-98923f497546",
                    "private": False,
                },
                "owner": {
                    "username": "codecov",
                    "service_id": "6ef29b63-aaaa-aaaa-aaaa-aaaa03f5cd49",
                },
            },
            {
                "repo": {
                    "name": "private",
                    "language": "python",
                    "branch": "main",
                    "service_id": "3edf54ab-cfe4-4049-aa70-5eb9f69f60d4",
                    "private": True,
                },
                "owner": {
                    "username": "codecov",
                    "service_id": "6ef29b63-aaaa-aaaa-aaaa-aaaa03f5cd49",
                },
            },
            {
                "repo": {
                    "name": "coverage.py",
                    "language": "python",
                    "branch": "main",
                    "service_id": "d08f4587-489f-4b55-abad-3d4f396d9862",
                    "private": False,
                },
                "owner": {
                    "username": "codecov",
                    "service_id": "6ef29b63-aaaa-aaaa-aaaa-aaaa03f5cd49",
                },
            },
            {
                "repo": {
                    "name": "integration-test-repo",
                    "language": "python",
                    "branch": "main",
                    "service_id": "4fab7a33-92dd-450b-8d12-ea1ab7816300",
                    "private": True,
                },
                "owner": {
                    "username": "codecov",
                    "service_id": "6ef29b63-aaaa-aaaa-aaaa-aaaa03f5cd49",
                },
            },
            {
                "repo": {
                    "name": "test-bb-integration-public",
                    "language": None,
                    "branch": "main",
                    "service_id": "2e219352-777c-4e2b-9a16-71211fbd4d93",
                    "private": False,
                },
                "owner": {
                    "username": "codecov",
                    "service_id": "6ef29b63-aaaa-aaaa-aaaa-aaaa03f5cd49",
                },
            },
        ]

        repos = []
        page_count = 0
        async for page in valid_handler.list_repos_generator("codecov"):
            repos.extend(page)
            page_count += 1

        assert page_count == 1
        assert sorted(repos, key=lambda x: x["repo"]["service_id"]) == sorted(
            expected_result, key=lambda x: x["repo"]["service_id"]
        )

    @pytest.mark.asyncio
    async def test_list_permissions(self, valid_handler, codecov_vcr):
        expected_result = [
            {
                "type": "repository_permission",
                "user": {
                    "display_name": "Thiago Ramos",
                    "account_id": "5bce04c759d0e84f8c7555e9",
                    "links": {
                        "self": {
                            "href": "https://bitbucket.org/!api/2.0/users/%7B9a01f37b-b1b2-40c5-8c5e-1a39f4b5e645%7D"
                        },
                        "html": {
                            "href": "https://bitbucket.org/%7B9a01f37b-b1b2-40c5-8c5e-1a39f4b5e645%7D/"
                        },
                        "avatar": {
                            "href": "https://avatar-management--avatars.us-west-2.prod.public.atl-paas.net/initials/TR-6.png"
                        },
                    },
                    "type": "user",
                    "nickname": "thiago",
                    "uuid": "{9a01f37b-b1b2-40c5-8c5e-1a39f4b5e645}",
                },
                "repository": {
                    "full_name": "codecov/ci-repo",
                    "type": "repository",
                    "name": "ci-repo",
                    "links": {
                        "self": {
                            "href": "https://bitbucket.org/!api/2.0/repositories/codecov/ci-repo"
                        },
                        "html": {"href": "https://bitbucket.org/codecov/ci-repo"},
                        "avatar": {
                            "href": "https://bytebucket.org/ravatar/%7Ba980e378-088f-48a8-9850-98923f497546%7D?ts=default"
                        },
                    },
                    "uuid": "{a980e378-088f-48a8-9850-98923f497546}",
                },
                "permission": "admin",
            },
            {
                "type": "repository_permission",
                "user": {
                    "display_name": "Thiago Ramos",
                    "account_id": "5bce04c759d0e84f8c7555e9",
                    "links": {
                        "self": {
                            "href": "https://bitbucket.org/!api/2.0/users/%7B9a01f37b-b1b2-40c5-8c5e-1a39f4b5e645%7D"
                        },
                        "html": {
                            "href": "https://bitbucket.org/%7B9a01f37b-b1b2-40c5-8c5e-1a39f4b5e645%7D/"
                        },
                        "avatar": {
                            "href": "https://avatar-management--avatars.us-west-2.prod.public.atl-paas.net/initials/TR-6.png"
                        },
                    },
                    "type": "user",
                    "nickname": "thiago",
                    "uuid": "{9a01f37b-b1b2-40c5-8c5e-1a39f4b5e645}",
                },
                "repository": {
                    "full_name": "codecov/private",
                    "type": "repository",
                    "name": "private",
                    "links": {
                        "self": {
                            "href": "https://bitbucket.org/!api/2.0/repositories/codecov/private"
                        },
                        "html": {"href": "https://bitbucket.org/codecov/private"},
                        "avatar": {
                            "href": "https://bytebucket.org/ravatar/%7B3edf54ab-cfe4-4049-aa70-5eb9f69f60d4%7D?ts=python"
                        },
                    },
                    "uuid": "{3edf54ab-cfe4-4049-aa70-5eb9f69f60d4}",
                },
                "permission": "admin",
            },
            {
                "type": "repository_permission",
                "user": {
                    "display_name": "Thiago Ramos",
                    "account_id": "5bce04c759d0e84f8c7555e9",
                    "links": {
                        "self": {
                            "href": "https://bitbucket.org/!api/2.0/users/%7B9a01f37b-b1b2-40c5-8c5e-1a39f4b5e645%7D"
                        },
                        "html": {
                            "href": "https://bitbucket.org/%7B9a01f37b-b1b2-40c5-8c5e-1a39f4b5e645%7D/"
                        },
                        "avatar": {
                            "href": "https://avatar-management--avatars.us-west-2.prod.public.atl-paas.net/initials/TR-6.png"
                        },
                    },
                    "type": "user",
                    "nickname": "thiago",
                    "uuid": "{9a01f37b-b1b2-40c5-8c5e-1a39f4b5e645}",
                },
                "repository": {
                    "full_name": "codecov/coverage.py",
                    "type": "repository",
                    "name": "coverage.py",
                    "links": {
                        "self": {
                            "href": "https://bitbucket.org/!api/2.0/repositories/codecov/coverage.py"
                        },
                        "html": {"href": "https://bitbucket.org/codecov/coverage.py"},
                        "avatar": {
                            "href": "https://bytebucket.org/ravatar/%7Bd08f4587-489f-4b55-abad-3d4f396d9862%7D?ts=python"
                        },
                    },
                    "uuid": "{d08f4587-489f-4b55-abad-3d4f396d9862}",
                },
                "permission": "admin",
            },
            {
                "type": "repository_permission",
                "user": {
                    "display_name": "Thiago Ramos",
                    "account_id": "5bce04c759d0e84f8c7555e9",
                    "links": {
                        "self": {
                            "href": "https://bitbucket.org/!api/2.0/users/%7B9a01f37b-b1b2-40c5-8c5e-1a39f4b5e645%7D"
                        },
                        "html": {
                            "href": "https://bitbucket.org/%7B9a01f37b-b1b2-40c5-8c5e-1a39f4b5e645%7D/"
                        },
                        "avatar": {
                            "href": "https://avatar-management--avatars.us-west-2.prod.public.atl-paas.net/initials/TR-6.png"
                        },
                    },
                    "type": "user",
                    "nickname": "thiago",
                    "uuid": "{9a01f37b-b1b2-40c5-8c5e-1a39f4b5e645}",
                },
                "repository": {
                    "full_name": "ThiagoCodecov/example-python",
                    "type": "repository",
                    "name": "example-python",
                    "links": {
                        "self": {
                            "href": "https://bitbucket.org/!api/2.0/repositories/ThiagoCodecov/example-python"
                        },
                        "html": {
                            "href": "https://bitbucket.org/ThiagoCodecov/example-python"
                        },
                        "avatar": {
                            "href": "https://bytebucket.org/ravatar/%7Ba8c50527-2c3a-480e-afe1-7700e2b00074%7D?ts=default"
                        },
                    },
                    "uuid": "{a8c50527-2c3a-480e-afe1-7700e2b00074}",
                },
                "permission": "admin",
            },
            {
                "type": "repository_permission",
                "user": {
                    "display_name": "Thiago Ramos",
                    "account_id": "5bce04c759d0e84f8c7555e9",
                    "links": {
                        "self": {
                            "href": "https://bitbucket.org/!api/2.0/users/%7B9a01f37b-b1b2-40c5-8c5e-1a39f4b5e645%7D"
                        },
                        "html": {
                            "href": "https://bitbucket.org/%7B9a01f37b-b1b2-40c5-8c5e-1a39f4b5e645%7D/"
                        },
                        "avatar": {
                            "href": "https://avatar-management--avatars.us-west-2.prod.public.atl-paas.net/initials/TR-6.png"
                        },
                    },
                    "type": "user",
                    "nickname": "thiago",
                    "uuid": "{9a01f37b-b1b2-40c5-8c5e-1a39f4b5e645}",
                },
                "repository": {
                    "full_name": "codecov/integration-test-repo",
                    "type": "repository",
                    "name": "integration-test-repo",
                    "links": {
                        "self": {
                            "href": "https://bitbucket.org/!api/2.0/repositories/codecov/integration-test-repo"
                        },
                        "html": {
                            "href": "https://bitbucket.org/codecov/integration-test-repo"
                        },
                        "avatar": {
                            "href": "https://bytebucket.org/ravatar/%7B4fab7a33-92dd-450b-8d12-ea1ab7816300%7D?ts=python"
                        },
                    },
                    "uuid": "{4fab7a33-92dd-450b-8d12-ea1ab7816300}",
                },
                "permission": "admin",
            },
            {
                "type": "repository_permission",
                "user": {
                    "display_name": "Thiago Ramos",
                    "account_id": "5bce04c759d0e84f8c7555e9",
                    "links": {
                        "self": {
                            "href": "https://bitbucket.org/!api/2.0/users/%7B9a01f37b-b1b2-40c5-8c5e-1a39f4b5e645%7D"
                        },
                        "html": {
                            "href": "https://bitbucket.org/%7B9a01f37b-b1b2-40c5-8c5e-1a39f4b5e645%7D/"
                        },
                        "avatar": {
                            "href": "https://avatar-management--avatars.us-west-2.prod.public.atl-paas.net/initials/TR-6.png"
                        },
                    },
                    "type": "user",
                    "nickname": "thiago",
                    "uuid": "{9a01f37b-b1b2-40c5-8c5e-1a39f4b5e645}",
                },
                "repository": {
                    "full_name": "codecov/test-bb-integration-public",
                    "type": "repository",
                    "name": "test-bb-integration-public",
                    "links": {
                        "self": {
                            "href": "https://bitbucket.org/!api/2.0/repositories/codecov/test-bb-integration-public"
                        },
                        "html": {
                            "href": "https://bitbucket.org/codecov/test-bb-integration-public"
                        },
                        "avatar": {
                            "href": "https://bytebucket.org/ravatar/%7B2e219352-777c-4e2b-9a16-71211fbd4d93%7D?ts=markdown"
                        },
                    },
                    "uuid": "{2e219352-777c-4e2b-9a16-71211fbd4d93}",
                },
                "permission": "admin",
            },
            {
                "type": "repository_permission",
                "user": {
                    "display_name": "Thiago Ramos",
                    "account_id": "5bce04c759d0e84f8c7555e9",
                    "links": {
                        "self": {
                            "href": "https://bitbucket.org/!api/2.0/users/%7B9a01f37b-b1b2-40c5-8c5e-1a39f4b5e645%7D"
                        },
                        "html": {
                            "href": "https://bitbucket.org/%7B9a01f37b-b1b2-40c5-8c5e-1a39f4b5e645%7D/"
                        },
                        "avatar": {
                            "href": "https://avatar-management--avatars.us-west-2.prod.public.atl-paas.net/initials/TR-6.png"
                        },
                    },
                    "type": "user",
                    "nickname": "thiago",
                    "uuid": "{9a01f37b-b1b2-40c5-8c5e-1a39f4b5e645}",
                },
                "repository": {
                    "full_name": "codecov/test-private-repo-2",
                    "type": "repository",
                    "name": "test-private-repo-2",
                    "links": {
                        "self": {
                            "href": "https://bitbucket.org/!api/2.0/repositories/codecov/test-private-repo-2"
                        },
                        "html": {
                            "href": "https://bitbucket.org/codecov/test-private-repo-2"
                        },
                        "avatar": {
                            "href": "https://bytebucket.org/ravatar/%7Bd215b8f1-b862-4fae-9bc8-c2c8ea2e1a70%7D?ts=python"
                        },
                    },
                    "uuid": "{d215b8f1-b862-4fae-9bc8-c2c8ea2e1a70}",
                },
                "permission": "admin",
            },
        ]
        res = await valid_handler.list_permissions()
        assert res == expected_result

    @pytest.mark.asyncio
    async def test_list_repos_no_username(self, valid_handler, codecov_vcr):
        expected_result = [
            {
                "repo": {
                    "name": "example-python",
                    "language": None,
                    "branch": "main",
                    "service_id": "a8c50527-2c3a-480e-afe1-7700e2b00074",
                    "private": True,
                },
                "owner": {
                    "username": "ThiagoCodecov",
                    "service_id": "9a01f37b-b1b2-40c5-8c5e-1a39f4b5e645",
                },
            }
        ]
        res = await valid_handler.list_repos()
        print(res)
        assert sorted(res, key=lambda x: x["repo"]["service_id"]) == sorted(
            expected_result, key=lambda x: x["repo"]["service_id"]
        )

    @pytest.mark.asyncio
    async def test_list_teams(self, valid_handler, codecov_vcr):
        expected_result = [
            {
                "name": "thiagorramostestnumbar3",
                "id": "d7c73e87-90ab-450f-bb5f-39e6a5870456",
                "email": None,
                "username": "thiagorramostestnumbar3",
            },
            {
                "name": "ThiagoRRamostest2",
                "id": "33b5f87a-bda0-40c2-ba1b-9eb892492290",
                "email": None,
                "username": "thiagorramostest2",
            },
            {
                "name": "ThiagoRRamosanotherw",
                "id": "11e04628-2c7b-4d89-9319-e7eed8818e56",
                "email": None,
                "username": "thiagorramosanotherw",
            },
            {
                "name": "ThiagoRRamosworkspace",
                "id": "727d78e8-7431-4532-9519-1e5fe2b61d4b",
                "email": None,
                "username": "thiagorramosworkspace",
            },
            {
                "name": "ThiagoCodecovbanana",
                "id": "68f2da06-b2f8-4f00-92fa-32bd60df9d27",
                "email": None,
                "username": "thiagocodecovbanana",
            },
            {
                "name": "Thiago Ramos",
                "id": "9a01f37b-b1b2-40c5-8c5e-1a39f4b5e645",
                "email": None,
                "username": "ThiagoCodecov",
            },
        ]
        res = await valid_handler.list_teams()
        print(res)
        assert res == expected_result

    @pytest.mark.asyncio
    async def test_list_top_level_files_multiple_pages(
        self, valid_handler, codecov_vcr
    ):
        expected_result = [
            {"path": "awesome", "type": "folder"},
            {"path": "kaploft", "type": "folder"},
            {"path": "tests", "type": "folder"},
            {"path": ".coverage", "type": "file"},
            {"path": ".gitignore", "type": "file"},
            {"path": "README.rst", "type": "file"},
            {"path": "__init__.py", "type": "file"},
            {"path": "a1.txt", "type": "file"},
            {"path": "a10.txt", "type": "file"},
            {"path": "a11.txt", "type": "file"},
            {"path": "a2.txt", "type": "file"},
            {"path": "a3.txt", "type": "file"},
            {"path": "a4.txt", "type": "file"},
            {"path": "a5.txt", "type": "file"},
            {"path": "a6.txt", "type": "file"},
            {"path": "a7.txt", "type": "file"},
            {"path": "a8.txt", "type": "file"},
            {"path": "a9.txt", "type": "file"},
            {"path": "bitbucket-pipelines.yml", "type": "file"},
            {"path": "coverage.xml", "type": "file"},
            {"path": "filet2.py", "type": "file"},
            {"path": "requirements.txt", "type": "file"},
        ]

        res = await valid_handler.list_top_level_files("second-branch")
        assert sorted(res, key=lambda x: x["path"]) == sorted(
            expected_result, key=lambda x: x["path"]
        )

    @pytest.mark.asyncio
    async def test_list_files(self, valid_handler, codecov_vcr):
        expected_result = [
            {"path": "tests/__pycache__", "type": "folder"},
            {"path": "tests/__init__.py", "type": "file"},
            {"path": "tests/test_k.py", "type": "file"},
        ]
        res = await valid_handler.list_files("second-branch", "tests")
        assert sorted(res, key=lambda x: x["path"]) == sorted(
            expected_result, key=lambda x: x["path"]
        )

    @pytest.mark.asyncio
    async def test_get_ancestors_tree(self, valid_handler, codecov_vcr):
        commitid = "6ae5f17"
        res = await valid_handler.get_ancestors_tree(commitid)
        assert res["commitid"] == "6ae5f1795a441884ed2847bb31154814ac01ef38"
        assert sorted([x["commitid"] for x in res["parents"]]) == [
            "8631ea09b9b689de0a348d5abf70bdd7273d2ae3"
        ]

    def test_get_href(self, valid_handler):
        expected_result = "https://bitbucket.org/ThiagoCodecov/example-python/commits/8631ea09b9b689de0a348d5abf70bdd7273d2ae3"
        res = valid_handler.get_href(
            Endpoints.commit_detail, commitid="8631ea09b9b689de0a348d5abf70bdd7273d2ae3"
        )
        assert res == expected_result

    @pytest.mark.asyncio
    async def test_is_student(self, valid_handler, codecov_vcr):
        res = await valid_handler.is_student()
        assert not res
