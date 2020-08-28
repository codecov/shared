import pytest

from shared.torngit.enums import Endpoints
from shared.torngit.exceptions import (
    TorngitObjectNotFoundError,
    TorngitServerUnreachableError,
    TorngitServer5xxCodeError,
    TorngitClientError,
    TorngitRepoNotFoundError,
)

from shared.torngit.github import Github
from tornado.httpclient import HTTPError


@pytest.fixture
def valid_handler():
    return Github(
        repo=dict(name="example-python"),
        owner=dict(username="ThiagoCodecov"),
        token=dict(key="test2d3454fe2s1xtot3dch9i939liacsgndapgf"),
    )


@pytest.fixture
def valid_but_no_permissions_handler():
    return Github(
        repo=dict(name="worker"),
        owner=dict(username="codecov"),
        token=dict(key="testyh3jmxkprygtinopr800pbmakt5j86ymqh33"),
    )


@pytest.fixture
def repo_doesnt_exist_handler():
    return Github(
        repo=dict(name="badrepo"),
        owner=dict(username="codecov"),
        token=dict(key="testao8tozi4d6k1rfn8chelvsq766tkycauxmja"),
    )


@pytest.fixture
def more_complex_handler():
    return Github(
        repo=dict(name="worker"),
        owner=dict(username="codecov"),
        token=dict(key="testnvebxku3hfiwi16ka7hff42y0jtf5fithlij"),
    )


class TestGithubTestCase(object):
    @pytest.mark.asyncio
    async def test_post_comment(self, valid_handler, codecov_vcr):
        expected_result = {
            "url": "https://api.github.com/repos/ThiagoCodecov/example-python/issues/comments/436811257",
            "html_url": "https://github.com/ThiagoCodecov/example-python/pull/1#issuecomment-436811257",
            "issue_url": "https://api.github.com/repos/ThiagoCodecov/example-python/issues/1",
            "id": 436811257,
            "node_id": "MDEyOklzc3VlQ29tbWVudDQzNjgxMTI1Nw==",
            "user": {
                "login": "ThiagoCodecov",
                "id": 44376991,
                "node_id": "MDQ6VXNlcjQ0Mzc2OTkx",
                "avatar_url": "https://avatars3.githubusercontent.com/u/44376991?v=4",
                "gravatar_id": "",
                "url": "https://api.github.com/users/ThiagoCodecov",
                "html_url": "https://github.com/ThiagoCodecov",
                "followers_url": "https://api.github.com/users/ThiagoCodecov/followers",
                "following_url": "https://api.github.com/users/ThiagoCodecov/following{/other_user}",
                "gists_url": "https://api.github.com/users/ThiagoCodecov/gists{/gist_id}",
                "starred_url": "https://api.github.com/users/ThiagoCodecov/starred{/owner}{/repo}",
                "subscriptions_url": "https://api.github.com/users/ThiagoCodecov/subscriptions",
                "organizations_url": "https://api.github.com/users/ThiagoCodecov/orgs",
                "repos_url": "https://api.github.com/users/ThiagoCodecov/repos",
                "events_url": "https://api.github.com/users/ThiagoCodecov/events{/privacy}",
                "received_events_url": "https://api.github.com/users/ThiagoCodecov/received_events",
                "type": "User",
                "site_admin": False,
            },
            "created_at": "2018-11-07T23:08:03Z",
            "updated_at": "2018-11-07T23:08:03Z",
            "author_association": "OWNER",
            "body": "Hello world",
        }

        res = await valid_handler.post_comment("1", "Hello world")
        print(res)
        assert res == expected_result

    @pytest.mark.asyncio
    async def test_get_authenticated_user(self, codecov_vcr):
        code = "a8d0f143cd8a98498773"
        handler = Github(
            oauth_consumer_token=dict(
                key="999247146557c3ba045c",
                secret="test6q9im2vau3pom1w4zkcm8zqbrkhqcaodsbce",
            )
        )
        res = await handler.get_authenticated_user(code)
        assert res == {
            "login": "ThiagoCodecov",
            "id": 44376991,
            "node_id": "MDQ6VXNlcjQ0Mzc2OTkx",
            "avatar_url": "https://avatars3.githubusercontent.com/u/44376991?v=4",
            "gravatar_id": "",
            "url": "https://api.github.com/users/ThiagoCodecov",
            "html_url": "https://github.com/ThiagoCodecov",
            "followers_url": "https://api.github.com/users/ThiagoCodecov/followers",
            "following_url": "https://api.github.com/users/ThiagoCodecov/following{/other_user}",
            "gists_url": "https://api.github.com/users/ThiagoCodecov/gists{/gist_id}",
            "starred_url": "https://api.github.com/users/ThiagoCodecov/starred{/owner}{/repo}",
            "subscriptions_url": "https://api.github.com/users/ThiagoCodecov/subscriptions",
            "organizations_url": "https://api.github.com/users/ThiagoCodecov/orgs",
            "repos_url": "https://api.github.com/users/ThiagoCodecov/repos",
            "events_url": "https://api.github.com/users/ThiagoCodecov/events{/privacy}",
            "received_events_url": "https://api.github.com/users/ThiagoCodecov/received_events",
            "type": "User",
            "site_admin": False,
            "name": "Thiago",
            "company": "@codecov ",
            "blog": "",
            "location": None,
            "email": None,
            "hireable": None,
            "bio": None,
            "twitter_username": None,
            "public_repos": 3,
            "public_gists": 0,
            "followers": 0,
            "following": 0,
            "created_at": "2018-10-22T17:51:44Z",
            "updated_at": "2020-08-27T23:16:04Z",
            "access_token": "testvhzseisglamvo88u0zo7zp4js3hlpoit20kg",
            "token_type": "bearer",
            "scope": "read:org,repo:status,user:email,write:repo_hook",
        }

    @pytest.mark.asyncio
    async def test_edit_comment(self, valid_handler, codecov_vcr):
        res = await valid_handler.edit_comment(
            "1", "436811257", "Hello world numbah 2 my friendo"
        )
        assert res is not None
        assert res["id"] == 436811257
        assert res["body"] == "Hello world numbah 2 my friendo"

    @pytest.mark.asyncio
    async def test_edit_comment_not_found(self, valid_handler, codecov_vcr):
        with pytest.raises(TorngitObjectNotFoundError):
            await valid_handler.edit_comment("1", "113979999", "Hello world number 2")

    @pytest.mark.asyncio
    async def test_delete_comment(self, valid_handler, codecov_vcr):
        assert await valid_handler.delete_comment("1", "436805577") is True

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
                    "branch": "master",
                    "commitid": "68946ef98daec68c7798459150982fc799c87d85",
                },
                "head": {
                    "branch": "reason/some-testing",
                    "commitid": "119c1907fb266f374b8440bbd70dccbea54daf8f",
                },
                "number": "1",
                "id": "1",
                "state": "merged",
                "title": "Creating new code for reasons no one knows",
                "author": {"id": "44376991", "username": "ThiagoCodecov"},
            },
        ),
    ]

    @pytest.mark.asyncio
    async def test_get_pull_request_way_more_than_250_results(
        self, valid_handler, codecov_vcr
    ):
        pull_id = "16"
        expected_result = {
            "base": {
                "branch": "master",
                "commitid": "d723f5cb5c9c9f48c47f2df97c47de20457d3fdc",
            },
            "head": {
                "branch": "thiago/f/big-pt",
                "commitid": "d55dc4ef748fd11537e50c9abed4ab1864fa1d94",
            },
            "number": pull_id,
            "id": pull_id,
            "state": "open",
            "title": "PR with more than 250 results",
            "author": {"id": "44376991", "username": "ThiagoCodecov"},
        }
        res = await valid_handler.get_pull_request(pull_id)
        assert res == expected_result

    @pytest.mark.asyncio
    @pytest.mark.parametrize("a,b", get_pull_request_test_data)
    async def test_get_pull_request(self, valid_handler, a, b, codecov_vcr):
        res = await valid_handler.get_pull_request(a)
        assert res == b

    @pytest.mark.asyncio
    async def test_api_client_error_unreachable(self, valid_handler, mocker):
        mocked_fetch = mocker.patch.object(Github, "fetch")
        mocked_fetch.side_effect = HTTPError(599, "message")
        method = "GET"
        url = "random_url"
        with pytest.raises(TorngitServerUnreachableError):
            await valid_handler.api(method, url)

    @pytest.mark.asyncio
    async def test_api_client_error_server_error(self, valid_handler, mocker):
        mocked_fetch = mocker.patch.object(Github, "fetch")
        mocked_fetch.side_effect = HTTPError(503, "message")
        method = "GET"
        url = "random_url"
        with pytest.raises(TorngitServer5xxCodeError):
            await valid_handler.api(method, url)

    @pytest.mark.asyncio
    async def test_api_client_error_client_error(self, valid_handler, mocker):
        mocked_fetch = mocker.patch.object(Github, "fetch")
        mock_response = mocker.MagicMock()
        mocked_fetch.side_effect = HTTPError(404, "message", mock_response)
        method = "GET"
        url = "random_url"
        with pytest.raises(TorngitClientError):
            await valid_handler.api(method, url)

    @pytest.mark.asyncio
    async def test_get_pull_request_commits(self, valid_handler, codecov_vcr):
        expected_result = ["a06aef4356ca35b34c5486269585288489e578db"]
        res = await valid_handler.get_pull_request_commits("1")
        assert res == expected_result

    @pytest.mark.asyncio
    async def test_get_pull_requests(self, valid_handler, codecov_vcr):
        expected_result = [1]
        res = await valid_handler.get_pull_requests()
        assert res == expected_result

    @pytest.mark.asyncio
    async def test_get_commit(self, valid_handler, codecov_vcr):
        expected_result = {
            "author": {
                "id": "8398772",
                "username": "jerrode",
                "email": "jerrod@fundersclub.com",
                "name": "Jerrod",
            },
            "message": "Adding 'include' term if multiple sources\n\nbased on a support ticket around multiple sources\r\n\r\nhttps://codecov.freshdesk.com/a/tickets/87",
            "parents": ["adb252173d2107fad86bcdcbc149884c2dd4c609"],
            "commitid": "6895b64",
            "timestamp": "2018-07-09T23:39:20Z",
        }

        commit = await valid_handler.get_commit("6895b64")
        assert commit["author"] == expected_result["author"]
        assert commit == expected_result

    @pytest.mark.asyncio
    async def test_get_commit_not_found(self, valid_handler, codecov_vcr):
        commitid = "abe3e94949d11471cc4e054f822d222254a4a4f8"
        with pytest.raises(TorngitObjectNotFoundError):
            await valid_handler.get_commit(commitid)

    @pytest.mark.asyncio
    async def test_get_commit_no_permissions(
        self, valid_but_no_permissions_handler, codecov_vcr
    ):
        commitid = "bbe3e94949d11471cc4e054f822d222254a4a4f8"
        with pytest.raises(TorngitRepoNotFoundError):
            await valid_but_no_permissions_handler.get_commit(commitid)

    @pytest.mark.asyncio
    async def test_get_commit_repo_doesnt_exist(
        self, valid_but_no_permissions_handler, codecov_vcr
    ):
        commitid = "bbe3e94949d11471cc4e054f822d222254a4a4f8"
        with pytest.raises(TorngitRepoNotFoundError) as ex:
            await valid_but_no_permissions_handler.get_commit(commitid)
        expected_response = '{"message":"Not Found","documentation_url":"https://developer.github.com/v3/repos/commits/#get-a-single-commit"}'
        exc = ex.value
        assert exc.response == expected_response

    @pytest.mark.asyncio
    async def test_get_commit_diff(self, valid_handler, codecov_vcr):
        expected_result = {
            "files": {
                ".travis.yml": {
                    "type": "modified",
                    "before": None,
                    "segments": [
                        {
                            "header": ["1", "3", "1", "5"],
                            "lines": [
                                "+sudo: false",
                                "+",
                                " language: python",
                                " ",
                                " python:",
                            ],
                        }
                    ],
                    "stats": {"added": 2, "removed": 0},
                }
            }
        }

        res = await valid_handler.get_commit_diff(
            "2be550c135cc13425cb2c239b9321e78dcfb787b"
        )
        assert res == expected_result

    @pytest.mark.asyncio
    async def test_get_commit_diff_not_found(self, valid_handler, codecov_vcr):
        with pytest.raises(TorngitObjectNotFoundError):
            await valid_handler.get_commit_diff(
                "3be850c135ccaa425cb2c239b9321e78dcfb78ff"
            )

    @pytest.mark.asyncio
    async def test_get_commit_statuses(self, more_complex_handler, codecov_vcr):
        res = await more_complex_handler.get_commit_statuses(
            "3fb5f4700da7818e561054ec26f5657de720717f"
        )
        assert res._statuses == [
            {
                "time": "2020-04-08T05:44:02Z",
                "state": "success",
                "description": "94.21% (+0.18%) compared to 48775c6",
                "url": "https://codecov.io/gh/codecov/worker/compare/48775c672437630c9c6f582ecfae5854a3617be2...3fb5f4700da7818e561054ec26f5657de720717f",
                "context": "codecov/project",
            },
            {
                "time": "2020-04-08T05:44:02Z",
                "state": "success",
                "description": "100.00% of diff hit (target 94.02%)",
                "url": "https://codecov.io/gh/codecov/worker/compare/48775c672437630c9c6f582ecfae5854a3617be2...3fb5f4700da7818e561054ec26f5657de720717f",
                "context": "codecov/patch",
            },
            {
                "time": "2020-04-08T20:39:33Z",
                "state": "success",
                "description": "Your tests passed on CircleCI!",
                "url": "https://circleci.com/gh/codecov/worker/2619?utm_campaign=vcs-integration-link&utm_medium=referral&utm_source=github-build-link",
                "context": "ci/circleci: build",
            },
            {
                "time": "2020-04-08T20:40:32Z",
                "state": "success",
                "description": "Your tests passed on CircleCI!",
                "url": "https://circleci.com/gh/codecov/worker/2620?utm_campaign=vcs-integration-link&utm_medium=referral&utm_source=github-build-link",
                "context": "ci/circleci: test",
            },
        ]
        assert res == "success"

    @pytest.mark.asyncio
    async def test_set_commit_statuses_then_get(self, valid_handler, codecov_vcr):
        commit_sha = "e999aac5b33acbca52601d2a655ab0ac46a1ffdf"
        target_url = "https://localhost:50036/github/codecov"
        statuses_to_set = [
            ("turtle", "success"),
            ("bird", "pending"),
            ("pig", "failure"),
            ("giant", "error"),
            ("turtle", "pending"),
            ("bird", "failure"),
            ("pig", "error"),
            ("giant", "success"),
            ("giant", "error"),
            ("giant", "success"),
            ("capybara", "success"),
        ]
        for i, val in enumerate(statuses_to_set):
            context, status = val
            res = await valid_handler.set_commit_status(
                commit_sha, status, context, f"{status} - {i} - {context}", target_url,
            )
        res = await valid_handler.get_commit_statuses(commit_sha)
        assert res._statuses == [
            {
                "time": "2020-04-08T20:51:26Z",
                "state": "pending",
                "description": "pending - 4 - turtle",
                "url": "https://localhost:50036/github/codecov",
                "context": "turtle",
            },
            {
                "time": "2020-04-08T20:51:27Z",
                "state": "failure",
                "description": "failure - 5 - bird",
                "url": "https://localhost:50036/github/codecov",
                "context": "bird",
            },
            {
                "time": "2020-04-08T20:51:27Z",
                "state": "error",
                "description": "error - 6 - pig",
                "url": "https://localhost:50036/github/codecov",
                "context": "pig",
            },
            {
                "time": "2020-04-08T20:51:29Z",
                "state": "success",
                "description": "success - 9 - giant",
                "url": "https://localhost:50036/github/codecov",
                "context": "giant",
            },
            {
                "time": "2020-04-08T20:51:29Z",
                "state": "success",
                "description": "success - 10 - capybara",
                "url": "https://localhost:50036/github/codecov",
                "context": "capybara",
            },
        ]
        assert res == "failure"

    @pytest.mark.asyncio
    async def test_set_commit_status(self, valid_handler, codecov_vcr):
        target_url = "https://localhost:50036/gitlab/codecov/ci-repo?ref=ad798926730aad14aadf72281204bdb85734fe67"
        expected_result = {
            "url": "https://api.github.com/repos/ThiagoCodecov/example-python/statuses/a06aef4356ca35b34c5486269585288489e578db",
            "avatar_url": "https://avatars0.githubusercontent.com/oa/930123?v=4",
            "id": 5770593059,
            "node_id": "MDEzOlN0YXR1c0NvbnRleHQ1NzcwNTkzMDU5",
            "state": "success",
            "description": "aaaaaaaaaa",
            "target_url": "https://localhost:50036/gitlab/codecov/ci-repo?ref=ad798926730aad14aadf72281204bdb85734fe67",
            "context": "context",
            "created_at": "2018-11-07T22:57:42Z",
            "updated_at": "2018-11-07T22:57:42Z",
            "creator": {
                "login": "ThiagoCodecov",
                "id": 44376991,
                "node_id": "MDQ6VXNlcjQ0Mzc2OTkx",
                "avatar_url": "https://avatars3.githubusercontent.com/u/44376991?v=4",
                "gravatar_id": "",
                "url": "https://api.github.com/users/ThiagoCodecov",
                "html_url": "https://github.com/ThiagoCodecov",
                "followers_url": "https://api.github.com/users/ThiagoCodecov/followers",
                "following_url": "https://api.github.com/users/ThiagoCodecov/following{/other_user}",
                "gists_url": "https://api.github.com/users/ThiagoCodecov/gists{/gist_id}",
                "starred_url": "https://api.github.com/users/ThiagoCodecov/starred{/owner}{/repo}",
                "subscriptions_url": "https://api.github.com/users/ThiagoCodecov/subscriptions",
                "organizations_url": "https://api.github.com/users/ThiagoCodecov/orgs",
                "repos_url": "https://api.github.com/users/ThiagoCodecov/repos",
                "events_url": "https://api.github.com/users/ThiagoCodecov/events{/privacy}",
                "received_events_url": "https://api.github.com/users/ThiagoCodecov/received_events",
                "type": "User",
                "site_admin": False,
            },
        }
        res = await valid_handler.set_commit_status(
            "a06aef4356ca35b34c5486269585288489e578db",
            "success",
            "context",
            "aaaaaaaaaa",
            target_url,
        )
        print(res)
        assert res == expected_result

    @pytest.mark.asyncio
    async def test_get_branches(self, valid_handler, codecov_vcr):
        expected_result = ["example", "future", "master", "reason/some-testing"]
        branches = sorted(await valid_handler.get_branches())
        assert list(map(lambda a: a[0], branches)) == expected_result

    @pytest.mark.asyncio
    async def test_post_webhook(self, valid_handler, codecov_vcr):
        url = "http://requestbin.net/r/1ecyaj51"
        events = [
            "push",
            "pull_request",
        ]
        name, secret = "a", "d"
        expected_result = {
            "type": "Repository",
            "id": 61813206,
            "name": "web",
            "active": True,
            "events": ["pull_request", "push"],
            "config": {
                "content_type": "json",
                "secret": "********",
                "url": "http://requestbin.net/r/1ecyaj51",
                "insecure_ssl": "0",
            },
            "updated_at": "2018-11-07T23:03:28Z",
            "created_at": "2018-11-07T23:03:28Z",
            "url": "https://api.github.com/repos/ThiagoCodecov/example-python/hooks/61813206",
            "test_url": "https://api.github.com/repos/ThiagoCodecov/example-python/hooks/61813206/test",
            "ping_url": "https://api.github.com/repos/ThiagoCodecov/example-python/hooks/61813206/pings",
            "last_response": {"code": None, "status": "unused", "message": None},
        }
        res = await valid_handler.post_webhook(name, url, events, secret)
        print(res)
        assert res == expected_result

    @pytest.mark.asyncio
    async def test_edit_webhook(self, valid_handler, codecov_vcr):
        url = "http://requestbin.net/r/1ecyaj51"
        events = ["project", "pull_request", "release"]
        new_name, secret = "new_name", "new_secret"
        expected_result = {
            "type": "Repository",
            "id": 61813206,
            "name": "web",
            "active": True,
            "events": ["pull_request", "project", "release"],
            "config": {
                "content_type": "json",
                "secret": "********",
                "url": "http://requestbin.net/r/1ecyaj51",
                "insecure_ssl": "0",
            },
            "updated_at": "2018-11-07T23:10:09Z",
            "created_at": "2018-11-07T23:03:28Z",
            "url": "https://api.github.com/repos/ThiagoCodecov/example-python/hooks/61813206",
            "test_url": "https://api.github.com/repos/ThiagoCodecov/example-python/hooks/61813206/test",
            "ping_url": "https://api.github.com/repos/ThiagoCodecov/example-python/hooks/61813206/pings",
            "last_response": {"code": 200, "message": "OK", "status": "active"},
        }
        res = await valid_handler.edit_webhook(
            "61813206", new_name, url, events, secret
        )
        assert res == expected_result

    @pytest.mark.asyncio
    async def test_delete_webhook(self, valid_handler, codecov_vcr):
        res = await valid_handler.delete_webhook("61813206")
        assert res is True

    @pytest.mark.asyncio
    async def test_delete_webhook_not_found(self, valid_handler, codecov_vcr):
        with pytest.raises(TorngitObjectNotFoundError):
            await valid_handler.delete_webhook("4742f011-8397-aa77-8876-5e9a06f10f98")

    @pytest.mark.asyncio
    async def test_get_authenticated(self, valid_handler, codecov_vcr):
        res = await valid_handler.get_authenticated()
        assert res == (True, True)

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
                                "header": ["9", "7", "9", "8"],
                                "lines": [
                                    " Overview",
                                    " --------",
                                    " ",
                                    "-Main website: `Codecov <https://codecov.io/>`_.",
                                    "+",
                                    "+website: `Codecov <https://codecov.io/>`_.",
                                    " ",
                                    " .. code-block:: shell-session",
                                    " ",
                                ],
                            },
                            {
                                "header": ["46", "12", "47", "19"],
                                "lines": [
                                    " ",
                                    " You may need to configure a ``.coveragerc`` file. Learn more `here <http://coverage.readthedocs.org/en/latest/config.html>`_. Start with this `generic .coveragerc <https://gist.github.com/codecov-io/bf15bde2c7db1a011b6e>`_ for example.",
                                    " ",
                                    "-We highly suggest adding `source` to your ``.coveragerc`` which solves a number of issues collecting coverage.",
                                    "+We highly suggest adding ``source`` to your ``.coveragerc``, which solves a number of issues collecting coverage.",
                                    " ",
                                    " .. code-block:: ini",
                                    " ",
                                    "    [run]",
                                    "    source=your_package_name",
                                    "+   ",
                                    "+If there are multiple sources, you instead should add ``include`` to your ``.coveragerc``",
                                    "+",
                                    "+.. code-block:: ini",
                                    "+",
                                    "+   [run]",
                                    "+   include=your_package_name/*",
                                    " ",
                                    " unittests",
                                    " ---------",
                                ],
                            },
                            {
                                "header": ["150", "5", "158", "4"],
                                "lines": [
                                    " * Twitter: `@codecov <https://twitter.com/codecov>`_.",
                                    " * Email: `hello@codecov.io <hello@codecov.io>`_.",
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
            "commits": [
                {
                    "commitid": "b92edba44fdd29fcc506317cc3ddeae1a723dd08",
                    "message": "Update README.rst",
                    "timestamp": "2018-07-09T23:51:16Z",
                    "author": {
                        "id": 8398772,
                        "username": "jerrode",
                        "name": "Jerrod",
                        "email": "jerrod@fundersclub.com",
                    },
                },
                {
                    "commitid": "c7f608036a3d2e89f8c59989ee213900c1ef39d1",
                    "message": "Update README.rst",
                    "timestamp": "2018-07-09T23:48:34Z",
                    "author": {
                        "id": 8398772,
                        "username": "jerrode",
                        "name": "Jerrod",
                        "email": "jerrod@fundersclub.com",
                    },
                },
                {
                    "commitid": "6895b6479dbe12b5cb3baa02416c6343ddb888b4",
                    "message": "Adding 'include' term if multiple sources\n\nbased on a support ticket around multiple sources\r\n\r\nhttps://codecov.freshdesk.com/a/tickets/87",
                    "timestamp": "2018-07-09T23:39:20Z",
                    "author": {
                        "id": 8398772,
                        "username": "jerrode",
                        "name": "Jerrod",
                        "email": "jerrod@fundersclub.com",
                    },
                },
                {
                    "commitid": "adb252173d2107fad86bcdcbc149884c2dd4c609",
                    "message": "Update README.rst",
                    "timestamp": "2018-04-26T08:39:32Z",
                    "author": {
                        "id": 11602092,
                        "username": "TomPed",
                        "name": "Thomas Pedbereznak",
                        "email": "tom@tomped.com",
                    },
                },
                {
                    "commitid": "6ae5f1795a441884ed2847bb31154814ac01ef38",
                    "message": "Update README.rst",
                    "timestamp": "2018-04-26T08:35:58Z",
                    "author": {
                        "id": 11602092,
                        "username": "TomPed",
                        "name": "Thomas Pedbereznak",
                        "email": "tom@tomped.com",
                    },
                },
            ],
        }

        res = await valid_handler.get_compare(base, head)
        print(res)
        assert sorted(list(res.keys())) == sorted(list(expected_result.keys()))
        assert res == expected_result

    @pytest.mark.asyncio
    async def test_get_compare_same_commit(self, valid_handler, codecov_vcr):
        base, head = "6ae5f17", "6ae5f17"
        expected_result = {
            "diff": {"files": {}},
            "commits": [
                {
                    "commitid": "6ae5f1795a441884ed2847bb31154814ac01ef38",
                    "author": {
                        "email": "tom@tomped.com",
                        "id": 11602092,
                        "name": "Thomas Pedbereznak",
                        "username": "TomPed",
                    },
                    "message": "Update README.rst",
                    "timestamp": "2018-04-26T08:35:58Z",
                }
            ],
        }
        res = await valid_handler.get_compare(base, head)
        assert sorted(list(res.keys())) == sorted(list(expected_result.keys()))
        assert len(res["commits"]) == len(expected_result["commits"])
        assert res["commits"][0] == expected_result["commits"][0]
        assert res == expected_result

    @pytest.mark.asyncio
    async def test_get_repository(self, valid_handler, codecov_vcr):
        expected_result = {
            "owner": {"service_id": 44376991, "username": "ThiagoCodecov"},
            "repo": {
                "branch": "master",
                "language": "python",
                "name": "example-python",
                "private": False,
                "service_id": 156617777,
                "fork": {
                    "owner": {"service_id": 8226205, "username": "codecov"},
                    "repo": {
                        "branch": "master",
                        "language": "python",
                        "name": "example-python",
                        "private": False,
                        "service_id": 24344106,
                    },
                },
            },
        }
        res = await valid_handler.get_repository()
        assert res["owner"] == expected_result["owner"]
        assert res["repo"] == expected_result["repo"]
        assert res == expected_result

    @pytest.mark.asyncio
    async def test_get_source_master(self, valid_handler, codecov_vcr):
        expected_result = {
            "commitid": "92aa2034f5283ff318a294116fe585e521d9f6d0",
            "content": b"import unittest\n\nimport awesome\n\n\nclass TestMethods(unittest.TestCase):\n    def test_add(self):\n        self.assertEqual(awesome.smile(), \":)\")\n\n\nif __name__ == '__main__':\n    unittest.main()\n",
        }
        path, ref = "tests.py", "master"
        res = await valid_handler.get_source(path, ref)
        print(res)
        assert res == expected_result

    @pytest.mark.asyncio
    async def test_get_source_random_commit(self, valid_handler, codecov_vcr):
        expected_result = {
            "commitid": "4d34acc61e7abe5536c84fec4fe9fd9b26311cc7",
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
        res = await valid_handler.list_repos()
        assert len(res) == 49
        print(res[-1])
        one_expected_result = {
            "owner": {"service_id": 44376991, "username": "ThiagoCodecov"},
            "repo": {
                "service_id": 156617777,
                "name": "example-python",
                "language": "python",
                "private": False,
                "branch": "master",
                "fork": {
                    "owner": {"service_id": 8226205, "username": "codecov"},
                    "repo": {
                        "service_id": 24344106,
                        "name": "example-python",
                        "language": "python",
                        "private": False,
                        "branch": "master",
                    },
                },
            },
        }

        assert one_expected_result in res

    @pytest.mark.asyncio
    async def test_list_teams(self, valid_handler, codecov_vcr):
        expected_result = [
            {
                "email": "hello@codecov.io",
                "id": "8226205",
                "name": "Codecov",
                "username": "codecov",
            }
        ]
        res = await valid_handler.list_teams()
        assert res == expected_result

    @pytest.mark.asyncio
    async def test_list_top_level_files(self, valid_handler, codecov_vcr):
        expected_result = [
            {"name": ".gitignore", "path": ".gitignore", "type": "file"},
            {"name": ".travis.yml", "path": ".travis.yml", "type": "file"},
            {"name": "README.rst", "path": "README.rst", "type": "file"},
            {"name": "awesome", "path": "awesome", "type": "folder"},
            {"name": "codecov", "path": "codecov", "type": "file"},
            {"name": "codecov.yaml", "path": "codecov.yaml", "type": "file"},
            {"name": "tests", "path": "tests", "type": "folder"},
        ]
        res = await valid_handler.list_top_level_files("master")
        assert sorted(res, key=lambda x: x["path"]) == sorted(
            expected_result, key=lambda x: x["path"]
        )

    @pytest.mark.asyncio
    async def test_list_files(self, valid_handler, codecov_vcr):
        expected_result = [
            {"name": "__init__.py", "path": "awesome/__init__.py", "type": "file"},
            {"name": "code_fib.py", "path": "awesome/code_fib.py", "type": "file"},
        ]
        res = await valid_handler.list_files("master", "awesome")
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
        expected_result = "https://github.com/ThiagoCodecov/example-python/commit/8631ea09b9b689de0a348d5abf70bdd7273d2ae3"
        res = valid_handler.get_href(
            Endpoints.commit_detail, commitid="8631ea09b9b689de0a348d5abf70bdd7273d2ae3"
        )
        assert res == expected_result

    @pytest.mark.asyncio
    async def test_get_pull_request_base_doesnt_match(self, valid_handler, codecov_vcr):
        pull_id = "15"
        expected_result = {
            "base": {
                "branch": "master",
                "commitid": "30cc1ed751a59fa9e7ad8e79fff41a6fe11ef5dd",
            },
            "head": {
                "branch": "thiago/test-1",
                "commitid": "2e2600aa09525e2e1e1d98b09de61454d29c94bb",
            },
            "number": "15",
            "id": "15",
            "state": "open",
            "title": "Thiago/test 1",
            "author": {"id": "44376991", "username": "ThiagoCodecov"},
        }
        res = await valid_handler.get_pull_request(pull_id)
        assert res == expected_result

    @pytest.mark.asyncio
    async def test_get_pull_request_base_partially_differs(self, codecov_vcr):
        handler = Github(
            repo=dict(name="codecov-api"),
            owner=dict(username="codecov"),
            token=dict(key="testdp7skub8zsbdcdyem0z9wt00zhbnibu2uyjb"),
        )
        pull_id = "110"
        expected_result = {
            "base": {
                "branch": "master",
                "commitid": "77141afbd13a1273f87cf02f7f32265ea19a3b77",
            },
            "head": {
                "branch": "ce-1314/gh-status-handler",
                "commitid": "b68cdcbf6cc1b270a16d8a82b67027bdbc087452",
            },
            "number": "110",
            "id": "110",
            "state": "open",
            "title": "CE-1314 GitHub Status Event Handler",
            "author": {"id": "5767537", "username": "pierce-m"},
        }
        res = await handler.get_pull_request(pull_id)
        assert res == expected_result

    @pytest.mark.asyncio
    async def test_get_workflow_run(self):
        handler = Github(
            repo=dict(name="codecov-test"),
            owner=dict(username="ibrahim0814"),
            token=dict(key="test9zwlbanm8k3m3394ihpwyqk08okirro3l3n0"),
        )
        expected_result = {
            "start_time": "2020-02-07T03:23:26Z",
            "finish_time": "2020-02-07T03:24:03Z",
            "status": "completed",
            "public": True,
            "slug": "ibrahim0814/codecov-test",
            "commit_sha": "c955f27de13dbbd6b113e069ed836b4d85903c6c",
        }
        run_id = "35734337"
        res = await handler.get_workflow_run(run_id)
        assert res == expected_result

    @pytest.mark.asyncio
    async def test_create_github_check(self, more_complex_handler, codecov_vcr):
        res = await more_complex_handler.create_check_run(
            "Test check",
            "0c71264642a03372df1534704f34d6a2242fdf2c",
            status="in_progress",
            token={"key": "v1.test7plgcp94kp45aqvz1zr1crhganpdm9t6u52i"},
        )
        assert res == 751486637

    @pytest.mark.asyncio
    async def test_update_github_check(self, more_complex_handler, codecov_vcr):
        res = await more_complex_handler.update_check_run(
            751486637,
            "success",
            token={"key": "v1.test7plgcp94kp45aqvz1zr1crhganpdm9t6u52i"},
        )
        expected_result = {
            "id": 751486637,
            "node_id": "MDg6Q2hlY2tSdW43NTE0ODY2Mzc=",
            "head_sha": "0c71264642a03372df1534704f34d6a2242fdf2c",
            "external_id": "",
            "url": "https://api.github.com/repos/codecov/worker/check-runs/751486637",
            "html_url": "https://github.com/codecov/worker/runs/751486637",
            "details_url": "https://stage-web.codecov.dev",
            "status": "completed",
            "conclusion": "success",
            "started_at": "2020-06-08T20:38:11Z",
            "completed_at": "2020-06-08T21:07:39Z",
            "output": {
                "title": None,
                "summary": None,
                "text": None,
                "annotations_count": 0,
                "annotations_url": "https://api.github.com/repos/codecov/worker/check-runs/751486637/annotations",
            },
            "name": "Test check",
            "check_suite": {"id": 772837618},
            "app": {
                "id": 67788,
                "slug": "codecov-app-integration-testing",
                "node_id": "MDM6QXBwNjc3ODg=",
                "owner": {
                    "login": "codecov",
                    "id": 8226205,
                    "node_id": "MDEyOk9yZ2FuaXphdGlvbjgyMjYyMDU=",
                    "avatar_url": "https://avatars3.githubusercontent.com/u/8226205?v=4",
                    "gravatar_id": "",
                    "url": "https://api.github.com/users/codecov",
                    "html_url": "https://github.com/codecov",
                    "followers_url": "https://api.github.com/users/codecov/followers",
                    "following_url": "https://api.github.com/users/codecov/following{/other_user}",
                    "gists_url": "https://api.github.com/users/codecov/gists{/gist_id}",
                    "starred_url": "https://api.github.com/users/codecov/starred{/owner}{/repo}",
                    "subscriptions_url": "https://api.github.com/users/codecov/subscriptions",
                    "organizations_url": "https://api.github.com/users/codecov/orgs",
                    "repos_url": "https://api.github.com/users/codecov/repos",
                    "events_url": "https://api.github.com/users/codecov/events{/privacy}",
                    "received_events_url": "https://api.github.com/users/codecov/received_events",
                    "type": "Organization",
                    "site_admin": False,
                },
                "name": "Codecov App Integration - Testing",
                "description": "An app used for the github app integration in test envrionments",
                "external_url": "https://stage-web.codecov.dev",
                "html_url": "https://github.com/apps/codecov-app-integration-testing",
                "created_at": "2020-06-06T01:35:43Z",
                "updated_at": "2020-06-06T01:35:43Z",
                "permissions": {
                    "administration": "read",
                    "checks": "write",
                    "contents": "read",
                    "issues": "read",
                    "members": "read",
                    "metadata": "read",
                    "pull_requests": "write",
                    "statuses": "write",
                },
                "events": [
                    "check_run",
                    "check_suite",
                    "create",
                    "delete",
                    "fork",
                    "membership",
                    "public",
                    "pull_request",
                    "push",
                    "release",
                    "repository",
                    "status",
                    "team_add",
                ],
            },
            "pull_requests": [
                {
                    "url": "https://api.github.com/repos/codecov/worker/pulls/336",
                    "id": 425229535,
                    "number": 336,
                    "head": {
                        "ref": "fb_message_mixin",
                        "sha": "0c71264642a03372df1534704f34d6a2242fdf2c",
                        "repo": {
                            "id": 157271496,
                            "url": "https://api.github.com/repos/codecov/worker",
                            "name": "worker",
                        },
                    },
                    "base": {
                        "ref": "master",
                        "sha": "2a5a8741a8fd0d9180f9e8b907442ac4b7a37c67",
                        "repo": {
                            "id": 157271496,
                            "url": "https://api.github.com/repos/codecov/worker",
                            "name": "worker",
                        },
                    },
                }
            ],
        }
        assert res == expected_result

    @pytest.mark.asyncio
    async def test_get_github_check_runs_no_params(
        self, more_complex_handler, codecov_vcr
    ):
        with pytest.raises(Exception):
            await more_complex_handler.get_check_runs(
                name="Test check",
                token={"key": "v1.test7plgcp94kp45aqvz1zr1crhganpdm9t6u52i"},
            )

    @pytest.mark.asyncio
    async def test_get_github_check_runs(self, more_complex_handler, codecov_vcr):
        res = await more_complex_handler.get_check_runs(
            name="Test check",
            head_sha="0c71264642a03372df1534704f34d6a2242fdf2c",
            token={"key": "v1.test7plgcp94kp45aqvz1zr1crhganpdm9t6u52i"},
        )
        expected_result = {
            "total_count": 1,
            "check_runs": [
                {
                    "id": 751486637,
                    "node_id": "MDg6Q2hlY2tSdW43NTE0ODY2Mzc=",
                    "head_sha": "0c71264642a03372df1534704f34d6a2242fdf2c",
                    "external_id": "",
                    "url": "https://api.github.com/repos/codecov/worker/check-runs/751486637",
                    "html_url": "https://github.com/codecov/worker/runs/751486637",
                    "details_url": "https://stage-web.codecov.dev",
                    "status": "in_progress",
                    "conclusion": None,
                    "started_at": "2020-06-08T20:38:11Z",
                    "completed_at": None,
                    "output": {
                        "title": None,
                        "summary": None,
                        "text": None,
                        "annotations_count": 0,
                        "annotations_url": "https://api.github.com/repos/codecov/worker/check-runs/751486637/annotations",
                    },
                    "name": "Test check",
                    "check_suite": {"id": 772837618},
                    "app": {
                        "id": 67788,
                        "slug": "codecov-app-integration-testing",
                        "node_id": "MDM6QXBwNjc3ODg=",
                        "owner": {
                            "login": "codecov",
                            "id": 8226205,
                            "node_id": "MDEyOk9yZ2FuaXphdGlvbjgyMjYyMDU=",
                            "avatar_url": "https://avatars3.githubusercontent.com/u/8226205?v=4",
                            "gravatar_id": "",
                            "url": "https://api.github.com/users/codecov",
                            "html_url": "https://github.com/codecov",
                            "followers_url": "https://api.github.com/users/codecov/followers",
                            "following_url": "https://api.github.com/users/codecov/following{/other_user}",
                            "gists_url": "https://api.github.com/users/codecov/gists{/gist_id}",
                            "starred_url": "https://api.github.com/users/codecov/starred{/owner}{/repo}",
                            "subscriptions_url": "https://api.github.com/users/codecov/subscriptions",
                            "organizations_url": "https://api.github.com/users/codecov/orgs",
                            "repos_url": "https://api.github.com/users/codecov/repos",
                            "events_url": "https://api.github.com/users/codecov/events{/privacy}",
                            "received_events_url": "https://api.github.com/users/codecov/received_events",
                            "type": "Organization",
                            "site_admin": False,
                        },
                        "name": "Codecov App Integration - Testing",
                        "description": "An app used for the github app integration in test envrionments",
                        "external_url": "https://stage-web.codecov.dev",
                        "html_url": "https://github.com/apps/codecov-app-integration-testing",
                        "created_at": "2020-06-06T01:35:43Z",
                        "updated_at": "2020-06-06T01:35:43Z",
                        "permissions": {
                            "administration": "read",
                            "checks": "write",
                            "contents": "read",
                            "issues": "read",
                            "members": "read",
                            "metadata": "read",
                            "pull_requests": "write",
                            "statuses": "write",
                        },
                        "events": [
                            "check_run",
                            "check_suite",
                            "create",
                            "delete",
                            "fork",
                            "membership",
                            "public",
                            "pull_request",
                            "push",
                            "release",
                            "repository",
                            "status",
                            "team_add",
                        ],
                    },
                    "pull_requests": [
                        {
                            "url": "https://api.github.com/repos/codecov/worker/pulls/336",
                            "id": 425229535,
                            "number": 336,
                            "head": {
                                "ref": "fb_message_mixin",
                                "sha": "0c71264642a03372df1534704f34d6a2242fdf2c",
                                "repo": {
                                    "id": 157271496,
                                    "url": "https://api.github.com/repos/codecov/worker",
                                    "name": "worker",
                                },
                            },
                            "base": {
                                "ref": "master",
                                "sha": "2a5a8741a8fd0d9180f9e8b907442ac4b7a37c67",
                                "repo": {
                                    "id": 157271496,
                                    "url": "https://api.github.com/repos/codecov/worker",
                                    "name": "worker",
                                },
                            },
                        }
                    ],
                }
            ],
        }
        assert res == expected_result

    @pytest.mark.asyncio
    async def test_get_github_check_suite(self, more_complex_handler, codecov_vcr):
        res = await more_complex_handler.get_check_suites(
            "0c71264642a03372df1534704f34d6a2242fdf2c",
            token={"key": "v1.test7plgcp94kp45aqvz1zr1crhganpdm9t6u52i"},
        )
        expected_result = {
            "total_count": 1,
            "check_suites": [
                {
                    "id": 734165241,
                    "node_id": "MDEwOkNoZWNrU3VpdGU3MzQxNjUyNDE=",
                    "head_branch": "fb_message_mixin",
                    "head_sha": "0c71264642a03372df1534704f34d6a2242fdf2c",
                    "status": "queued",
                    "conclusion": None,
                    "url": "https://api.github.com/repos/codecov/worker/check-suites/734165241",
                    "before": "0000000000000000000000000000000000000000",
                    "after": "0c71264642a03372df1534704f34d6a2242fdf2c",
                    "pull_requests": [],
                    "app": {
                        "id": 9795,
                        "slug": "codecov-development",
                        "node_id": "MDM6QXBwOTc5NQ==",
                        "owner": {
                            "login": "codecov",
                            "id": 8226205,
                            "node_id": "MDEyOk9yZ2FuaXphdGlvbjgyMjYyMDU=",
                            "avatar_url": "https://avatars3.githubusercontent.com/u/8226205?v=4",
                            "gravatar_id": "",
                            "url": "https://api.github.com/users/codecov",
                            "html_url": "https://github.com/codecov",
                            "followers_url": "https://api.github.com/users/codecov/followers",
                            "following_url": "https://api.github.com/users/codecov/following{/other_user}",
                            "gists_url": "https://api.github.com/users/codecov/gists{/gist_id}",
                            "starred_url": "https://api.github.com/users/codecov/starred{/owner}{/repo}",
                            "subscriptions_url": "https://api.github.com/users/codecov/subscriptions",
                            "organizations_url": "https://api.github.com/users/codecov/orgs",
                            "repos_url": "https://api.github.com/users/codecov/repos",
                            "events_url": "https://api.github.com/users/codecov/events{/privacy}",
                            "received_events_url": "https://api.github.com/users/codecov/received_events",
                            "type": "Organization",
                            "site_admin": False,
                        },
                        "name": "Codecov - Development",
                        "description": "",
                        "external_url": "https://codecov.io",
                        "html_url": "https://github.com/apps/codecov-development",
                        "created_at": "2018-03-07T16:53:38Z",
                        "updated_at": "2019-05-13T23:46:55Z",
                        "permissions": {
                            "administration": "write",
                            "checks": "write",
                            "contents": "write",
                            "deployments": "write",
                            "issues": "write",
                            "members": "write",
                            "metadata": "read",
                            "organization_projects": "write",
                            "pages": "write",
                            "pull_requests": "write",
                            "repository_projects": "write",
                            "statuses": "write",
                            "team_discussions": "write",
                        },
                        "events": [],
                    },
                    "created_at": "2020-05-29T17:19:34Z",
                    "updated_at": "2020-05-29T17:19:34Z",
                    "latest_check_runs_count": 0,
                    "check_runs_url": "https://api.github.com/repos/codecov/worker/check-suites/734165241/check-runs",
                    "head_commit": {
                        "id": "0c71264642a03372df1534704f34d6a2242fdf2c",
                        "tree_id": "d11e0eb1647a4459d9b441ac23be9acf55ea10a1",
                        "message": "Added Message Mixin",
                        "timestamp": "2020-05-29T17:19:21Z",
                        "author": {
                            "name": "Felipe Ballesteros",
                            "email": "felipe@codecov.io",
                        },
                        "committer": {
                            "name": "Felipe Ballesteros",
                            "email": "felipe@codecov.io",
                        },
                    },
                    "repository": {
                        "id": 157271496,
                        "node_id": "MDEwOlJlcG9zaXRvcnkxNTcyNzE0OTY=",
                        "name": "worker",
                        "full_name": "codecov/worker",
                        "private": True,
                        "owner": {
                            "login": "codecov",
                            "id": 8226205,
                            "node_id": "MDEyOk9yZ2FuaXphdGlvbjgyMjYyMDU=",
                            "avatar_url": "https://avatars3.githubusercontent.com/u/8226205?v=4",
                            "gravatar_id": "",
                            "url": "https://api.github.com/users/codecov",
                            "html_url": "https://github.com/codecov",
                            "followers_url": "https://api.github.com/users/codecov/followers",
                            "following_url": "https://api.github.com/users/codecov/following{/other_user}",
                            "gists_url": "https://api.github.com/users/codecov/gists{/gist_id}",
                            "starred_url": "https://api.github.com/users/codecov/starred{/owner}{/repo}",
                            "subscriptions_url": "https://api.github.com/users/codecov/subscriptions",
                            "organizations_url": "https://api.github.com/users/codecov/orgs",
                            "repos_url": "https://api.github.com/users/codecov/repos",
                            "events_url": "https://api.github.com/users/codecov/events{/privacy}",
                            "received_events_url": "https://api.github.com/users/codecov/received_events",
                            "type": "Organization",
                            "site_admin": False,
                        },
                        "html_url": "https://github.com/codecov/worker",
                        "description": "Code for Background Workers of Codecov",
                        "fork": False,
                        "url": "https://api.github.com/repos/codecov/worker",
                        "forks_url": "https://api.github.com/repos/codecov/worker/forks",
                        "keys_url": "https://api.github.com/repos/codecov/worker/keys{/key_id}",
                        "collaborators_url": "https://api.github.com/repos/codecov/worker/collaborators{/collaborator}",
                        "teams_url": "https://api.github.com/repos/codecov/worker/teams",
                        "hooks_url": "https://api.github.com/repos/codecov/worker/hooks",
                        "issue_events_url": "https://api.github.com/repos/codecov/worker/issues/events{/number}",
                        "events_url": "https://api.github.com/repos/codecov/worker/events",
                        "assignees_url": "https://api.github.com/repos/codecov/worker/assignees{/user}",
                        "branches_url": "https://api.github.com/repos/codecov/worker/branches{/branch}",
                        "tags_url": "https://api.github.com/repos/codecov/worker/tags",
                        "blobs_url": "https://api.github.com/repos/codecov/worker/git/blobs{/sha}",
                        "git_tags_url": "https://api.github.com/repos/codecov/worker/git/tags{/sha}",
                        "git_refs_url": "https://api.github.com/repos/codecov/worker/git/refs{/sha}",
                        "trees_url": "https://api.github.com/repos/codecov/worker/git/trees{/sha}",
                        "statuses_url": "https://api.github.com/repos/codecov/worker/statuses/{sha}",
                        "languages_url": "https://api.github.com/repos/codecov/worker/languages",
                        "stargazers_url": "https://api.github.com/repos/codecov/worker/stargazers",
                        "contributors_url": "https://api.github.com/repos/codecov/worker/contributors",
                        "subscribers_url": "https://api.github.com/repos/codecov/worker/subscribers",
                        "subscription_url": "https://api.github.com/repos/codecov/worker/subscription",
                        "commits_url": "https://api.github.com/repos/codecov/worker/commits{/sha}",
                        "git_commits_url": "https://api.github.com/repos/codecov/worker/git/commits{/sha}",
                        "comments_url": "https://api.github.com/repos/codecov/worker/comments{/number}",
                        "issue_comment_url": "https://api.github.com/repos/codecov/worker/issues/comments{/number}",
                        "contents_url": "https://api.github.com/repos/codecov/worker/contents/{+path}",
                        "compare_url": "https://api.github.com/repos/codecov/worker/compare/{base}...{head}",
                        "merges_url": "https://api.github.com/repos/codecov/worker/merges",
                        "archive_url": "https://api.github.com/repos/codecov/worker/{archive_format}{/ref}",
                        "downloads_url": "https://api.github.com/repos/codecov/worker/downloads",
                        "issues_url": "https://api.github.com/repos/codecov/worker/issues{/number}",
                        "pulls_url": "https://api.github.com/repos/codecov/worker/pulls{/number}",
                        "milestones_url": "https://api.github.com/repos/codecov/worker/milestones{/number}",
                        "notifications_url": "https://api.github.com/repos/codecov/worker/notifications{?since,all,participating}",
                        "labels_url": "https://api.github.com/repos/codecov/worker/labels{/name}",
                        "releases_url": "https://api.github.com/repos/codecov/worker/releases{/id}",
                        "deployments_url": "https://api.github.com/repos/codecov/worker/deployments",
                    },
                }
            ],
        }
        assert res == expected_result
