import httpx
import pytest
import respx

from urllib.parse import urlparse, parse_qsl

from shared.torngit.github import Github
from shared.torngit.base import TokenType

from shared.torngit.exceptions import (
    TorngitServerUnreachableError,
    TorngitServer5xxCodeError,
    TorngitClientError,
    TorngitRateLimitError,
    TorngitUnauthorizedError,
)


@pytest.fixture
def respx_vcr():
    with respx.mock as v:
        yield v


@pytest.fixture
def valid_handler():
    return Github(
        repo=dict(name="example-python"),
        owner=dict(username="ThiagoCodecov"),
        token=dict(key="some_key"),
    )


class TestUnitGithub(object):
    @pytest.mark.asyncio
    async def test_api_client_error_unreachable(self, valid_handler, mocker):
        client = mocker.MagicMock(
            request=mocker.AsyncMock(return_value=mocker.MagicMock(status_code=599))
        )
        method = "GET"
        url = "random_url"
        with pytest.raises(TorngitServerUnreachableError):
            await valid_handler.api(client, method, url)

    @pytest.mark.asyncio
    async def test_api_client_error_unauthorized(self, valid_handler, mocker):
        client = mocker.MagicMock(
            request=mocker.AsyncMock(return_value=mocker.MagicMock(status_code=401))
        )
        method = "GET"
        url = "random_url"
        with pytest.raises(TorngitUnauthorizedError):
            await valid_handler.api(client, method, url)

    @pytest.mark.asyncio
    async def test_api_client_error_ratelimit_reached(self):
        with respx.mock:
            my_route = respx.get("https://api.github.com/endpoint").mock(
                return_value=httpx.Response(
                    status_code=403,
                    headers={
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": "1350085394",
                    },
                )
            )
            handler = Github(
                repo=dict(name="aaaaa"),
                owner=dict(username="aaaaa"),
                token=dict(key="aaaaa"),
            )
            with pytest.raises(TorngitRateLimitError) as excinfo:
                async with handler.get_client() as client:
                    res = await handler.api(client, "get", "/endpoint")
            assert excinfo.value.code == 403
            assert excinfo.value.message == "Github API rate limit error: Forbidden"
            assert excinfo.value.reset == "1350085394"

    @pytest.mark.asyncio
    async def test_api_client_error_ratelimit_missing_header(self):
        with respx.mock:
            my_route = respx.get("https://api.github.com/endpoint").mock(
                return_value=httpx.Response(
                    status_code=403, headers={"X-RateLimit-Reset": "1350085394",},
                )
            )
            handler = Github(
                repo=dict(name="aaaaa"),
                owner=dict(username="aaaaa"),
                token=dict(key="aaaaa"),
            )
            with pytest.raises(TorngitClientError) as excinfo:
                async with handler.get_client() as client:
                    res = await handler.api(client, "get", "/endpoint")
            assert excinfo.value.code == 403

    @pytest.mark.asyncio
    async def test_api_client_error_server_error(self, valid_handler, mocker):
        client = mocker.MagicMock(
            request=mocker.AsyncMock(return_value=mocker.MagicMock(status_code=503))
        )
        method = "GET"
        url = "random_url"
        with pytest.raises(TorngitServer5xxCodeError):
            await valid_handler.api(client, method, url)

    @pytest.mark.asyncio
    async def test_api_client_error_client_error(self, valid_handler, mocker):
        client = mocker.MagicMock(
            request=mocker.AsyncMock(return_value=mocker.MagicMock(status_code=404))
        )
        method = "GET"
        url = "random_url"
        with pytest.raises(TorngitClientError):
            await valid_handler.api(client, method, url)

    @pytest.mark.asyncio
    async def test_socker_gaierror(self, mocker, valid_handler):
        client = mocker.MagicMock(
            request=mocker.AsyncMock(
                side_effect=httpx.TimeoutException("message", request="request")
            )
        )
        with pytest.raises(TorngitServerUnreachableError):
            await valid_handler.api(
                client, "get", "/repos/%s/branches" % valid_handler.slug, per_page=100,
            )

    @pytest.mark.asyncio
    async def test_api_client_query_params(self, valid_handler, mocker):
        client = mocker.MagicMock(
            request=mocker.AsyncMock(
                return_value=mocker.MagicMock(text="kowabunga", status_code=200)
            )
        )
        method = "GET"
        url = "/random_url"
        query_params = {"qparam1": "a param", "qparam2": "another param"}
        res = await valid_handler.api(client, method, url, **query_params)
        assert res == "kowabunga"
        assert client.request.call_count == 1
        args, kwargs = client.request.call_args
        print(args)
        assert len(args) == 2
        built_url = args[1]
        parsed_url = urlparse(built_url)
        print(parsed_url)
        assert parsed_url.scheme == "https"
        assert parsed_url.netloc == "api.github.com"
        assert parsed_url.path == url
        assert parsed_url.params == ""
        assert parsed_url.fragment == ""
        query = dict(parse_qsl(parsed_url.query, keep_blank_values=True))
        assert query["qparam1"] == query_params["qparam1"]
        assert query["qparam2"] == query_params["qparam2"]

    def test_loggable_token(self, mocker, valid_handler):
        no_username_handler = Github(
            repo=dict(name="example-python"),
            owner=dict(username="ThiagoCodecov"),
            token=dict(key="some_key"),
        )
        assert no_username_handler.loggable_token(no_username_handler.token) == "f7CMr"
        with_username_handler = Github(
            repo=dict(name="example-python"),
            owner=dict(username="ThiagoCodecov"),
            token=dict(key="some_key", username="Thiago"),
        )
        assert (
            with_username_handler.loggable_token(with_username_handler.token)
            == "Thiago's token"
        )
        no_token_handler = Github(
            repo=dict(name="example-python"),
            owner=dict(username="ThiagoCodecov"),
            token=dict(key=None),
        )
        assert no_token_handler.loggable_token(no_token_handler.token) == "notoken"
        no_repo_handler = Github(
            repo=dict(),
            owner=dict(username="ThiagoCodecov"),
            token=dict(key="some_key"),
        )
        assert no_repo_handler.loggable_token(no_repo_handler.token) == "2vwGK"

    @pytest.mark.asyncio
    async def test_api_retries(self, valid_handler, mocker):
        client = mocker.MagicMock(
            request=mocker.AsyncMock(
                side_effect=[
                    mocker.MagicMock(text="NOTHERE", status_code=401),
                    mocker.MagicMock(text="FOUND", status_code=200),
                ]
            )
        )
        method = "GET"
        url = "random_url"
        res = await valid_handler.api(client, method, url, statuses_to_retry=[401])
        assert res == "FOUND"

    @pytest.mark.asyncio
    async def test_api_almost_too_many_retries(self, valid_handler, mocker):
        client = mocker.MagicMock(
            request=mocker.AsyncMock(
                side_effect=[
                    mocker.MagicMock(text="NOTHERE", status_code=401),
                    mocker.MagicMock(text="NOTHERE", status_code=401),
                    mocker.MagicMock(text="FOUND", status_code=200),
                ]
            )
        )
        method = "GET"
        url = "random_url"
        res = await valid_handler.api(client, method, url, statuses_to_retry=[401])
        assert res == "FOUND"

    @pytest.mark.asyncio
    async def test_api_too_many_retries(self, valid_handler, mocker):
        client = mocker.MagicMock(
            request=mocker.AsyncMock(
                side_effect=[
                    mocker.MagicMock(text="NOTHERE", status_code=401),
                    mocker.MagicMock(text="NOTHERE", status_code=401),
                    mocker.MagicMock(text="NOTHERE", status_code=401),
                    mocker.MagicMock(text="FOUND", status_code=200),
                ]
            )
        )
        method = "GET"
        url = "random_url"
        with pytest.raises(TorngitClientError):
            await valid_handler.api(client, method, url, statuses_to_retry=[401])

    def test_get_token_by_type_if_none(self):
        instance = Github(
            token="token",
            token_type_mapping={
                TokenType.read: "read",
                TokenType.admin: "admin",
                TokenType.comment: "comment",
                TokenType.status: "status",
            },
        )
        assert instance.get_token_by_type_if_none(None, TokenType.read) == "read"
        assert instance.get_token_by_type_if_none(None, TokenType.admin) == "admin"
        assert instance.get_token_by_type_if_none(None, TokenType.comment) == "comment"
        assert instance.get_token_by_type_if_none(None, TokenType.status) == "status"
        assert instance.get_token_by_type_if_none(
            {"key": "token_set_user"}, TokenType.read
        ) == {"key": "token_set_user"}
        assert instance.get_token_by_type_if_none(
            {"key": "token_set_user"}, TokenType.admin
        ) == {"key": "token_set_user"}
        assert instance.get_token_by_type_if_none(
            {"key": "token_set_user"}, TokenType.comment
        ) == {"key": "token_set_user"}
        assert instance.get_token_by_type_if_none(
            {"key": "token_set_user"}, TokenType.status
        ) == {"key": "token_set_user"}

    @pytest.mark.asyncio
    async def test_get_commit_diff_bad_encoding(self):
        with respx.mock:
            my_route = respx.get("https://api.github.com/endpoint").mock(
                return_value=httpx.Response(
                    status_code=200,
                    content="\xC4pple".encode("latin-1"),
                    headers={
                        "Content-Type": "application/vnd.github.v3.diff; charset=utf-8"
                    },
                )
            )
            handler = Github(
                repo=dict(name="aaaaa"),
                owner=dict(username="aaaaa"),
                token=dict(key="aaaaa"),
            )
            async with handler.get_client() as client:
                res = await handler.api(client, "get", "/endpoint")
            assert res == "Äpple"

    @pytest.mark.asyncio
    async def test_find_pull_request_uses_proper_query(self, mocker):
        with respx.mock:
            respx.get(
                url="https://api.github.com/search/issues?q=abcdef+repo%3Ausername%2Frepo_name+type%3Apr+state%3Aopen"
            ).mock(
                return_value=httpx.Response(
                    status_code=200,
                    # shortened version of the response
                    json={
                        "total_count": 1,
                        "incomplete_results": False,
                        "items": [
                            {
                                "id": 575148804,
                                "node_id": "MDExOlB1bGxSZXF1ZXN0MzgzMzQ4Nzc1",
                                "number": 18,
                                "title": "Thiago/base no base",
                                "labels": [],
                                "state": "open",
                                "locked": False,
                            }
                        ],
                    },
                    headers={"Content-Type": "application/json; charset=utf-8"},
                )
            )
            handler = Github(
                repo=dict(name="repo_name"),
                owner=dict(username="username"),
                token=dict(key="aaaaa"),
            )
            res = await handler.find_pull_request(commit="abcdef")
            assert res == 18

    @pytest.mark.asyncio
    async def test_post_comment(self, respx_vcr, valid_handler):
        mocked_response = respx_vcr.post(
            url="https://api.github.com/repos/ThiagoCodecov/example-python/issues/1/comments",
            json={"body": "Hello world"},
        ).mock(
            return_value=httpx.Response(
                status_code=201,
                json={
                    "url": "https://api.github.com/repos/ThiagoCodecov/example-python/issues/comments/708550750",
                    "html_url": "https://github.com/ThiagoCodecov/example-python/pull/1#issuecomment-708550750",
                    "issue_url": "https://api.github.com/repos/ThiagoCodecov/example-python/issues/1",
                    "id": 708550750,
                    "node_id": "MDEyOklzc3VlQ29tbWVudDcwODU1MDc1MA==",
                    "user": {
                        "login": "ThiagoCodecov",
                        "id": 44379999,
                        "node_id": "MDQ6VXNlcjQ0Mzc2OTkx",
                        "avatar_url": "https://avatars1.githubusercontent.com/u/44379999?u=d50e43da66b2dbe47099d854ebd3b489f1162d48&v=4",
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
                    "created_at": "2020-10-14T17:32:01Z",
                    "updated_at": "2020-10-14T17:32:01Z",
                    "author_association": "OWNER",
                    "body": "Hello world",
                    "performed_via_github_app": None,
                },
                headers={"Content-Type": "application/json; charset=utf-8"},
            )
        )
        expected_result = {
            "url": "https://api.github.com/repos/ThiagoCodecov/example-python/issues/comments/708550750",
            "html_url": "https://github.com/ThiagoCodecov/example-python/pull/1#issuecomment-708550750",
            "issue_url": "https://api.github.com/repos/ThiagoCodecov/example-python/issues/1",
            "id": 708550750,
            "node_id": "MDEyOklzc3VlQ29tbWVudDcwODU1MDc1MA==",
            "user": {
                "login": "ThiagoCodecov",
                "id": 44379999,
                "node_id": "MDQ6VXNlcjQ0Mzc2OTkx",
                "avatar_url": "https://avatars1.githubusercontent.com/u/44379999?u=d50e43da66b2dbe47099d854ebd3b489f1162d48&v=4",
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
            "created_at": "2020-10-14T17:32:01Z",
            "updated_at": "2020-10-14T17:32:01Z",
            "author_association": "OWNER",
            "body": "Hello world",
            "performed_via_github_app": None,
        }
        res = await valid_handler.post_comment("1", "Hello world")
        assert res == expected_result
        assert mocked_response.called is True

    @pytest.mark.asyncio
    async def test_list_teams(self, valid_handler, respx_vcr):
        mocked_response = respx_vcr.get(
            url="https://api.github.com/user/memberships/orgs?state=active&page=1",
        ).respond(
            status_code=200,
            json=[
                {
                    "url": "https://api.github.com/orgs/codecov/memberships/ThiagoCodecov",
                    "state": "active",
                    "role": "member",
                    "organization_url": "https://api.github.com/orgs/codecov",
                    "user": {
                        "login": "ThiagoCodecov",
                        "id": 44379999,
                        "node_id": "MDQ6VXNlcjQ0Mzc2OTkx",
                        "avatar_url": "https://avatars3.githubusercontent.com/u/44379999?v=4",
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
                    "organization": {
                        "login": "codecov",
                        "id": 8226999,
                        "node_id": "MDEyOk9yZ2FuaXphdGlvbjgyMjYyMDU=",
                        "url": "https://api.github.com/orgs/codecov",
                        "repos_url": "https://api.github.com/orgs/codecov/repos",
                        "events_url": "https://api.github.com/orgs/codecov/events",
                        "hooks_url": "https://api.github.com/orgs/codecov/hooks",
                        "issues_url": "https://api.github.com/orgs/codecov/issues",
                        "members_url": "https://api.github.com/orgs/codecov/members{/member}",
                        "public_members_url": "https://api.github.com/orgs/codecov/public_members{/member}",
                        "avatar_url": "https://avatars3.githubusercontent.com/u/8226999?v=4",
                        "description": "Empower developers with tools to improve code quality and testing.",
                    },
                },
                {
                    "url": "https://api.github.com/orgs/ThiagoCodecovTeam/memberships/ThiagoCodecov",
                    "state": "active",
                    "role": "admin",
                    "organization_url": "https://api.github.com/orgs/ThiagoCodecovTeam",
                    "user": {
                        "login": "ThiagoCodecov",
                        "id": 44379999,
                        "node_id": "MDQ6VXNlcjQ0Mzc2OTkx",
                        "avatar_url": "https://avatars3.githubusercontent.com/u/44379999?v=4",
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
                    "organization": {
                        "login": "ThiagoCodecovTeam",
                        "id": 57222756,
                        "node_id": "MDEyOk9yZ2FuaXphdGlvbjU3MjIyNzU2",
                        "url": "https://api.github.com/orgs/ThiagoCodecovTeam",
                        "repos_url": "https://api.github.com/orgs/ThiagoCodecovTeam/repos",
                        "events_url": "https://api.github.com/orgs/ThiagoCodecovTeam/events",
                        "hooks_url": "https://api.github.com/orgs/ThiagoCodecovTeam/hooks",
                        "issues_url": "https://api.github.com/orgs/ThiagoCodecovTeam/issues",
                        "members_url": "https://api.github.com/orgs/ThiagoCodecovTeam/members{/member}",
                        "public_members_url": "https://api.github.com/orgs/ThiagoCodecovTeam/public_members{/member}",
                        "avatar_url": "https://avatars0.githubusercontent.com/u/57222756?v=4",
                        "description": False,
                    },
                },
            ],
            headers={"Content-Type": "application/json; charset=utf-8"},
        )
        team_dicts = [
            (
                "https://api.github.com/users/codecov",
                {
                    "login": "codecov",
                    "id": 8226999,
                    "node_id": "MDEyOk9yZ2FuaXphdGlvbjgyMjYyMDU=",
                    "avatar_url": "https://avatars3.githubusercontent.com/u/8226999?v=4",
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
                    "name": "Codecov",
                    "company": None,
                    "blog": "https://codecov.io/",
                    "location": None,
                    "email": "hello@codecov.io",
                    "hireable": None,
                    "bio": "Empower developers with tools to improve code quality and testing.",
                    "twitter_username": None,
                    "public_repos": 97,
                    "public_gists": 0,
                    "followers": 0,
                    "following": 0,
                    "created_at": "2014-07-21T16:22:31Z",
                    "updated_at": "2020-10-28T19:29:26Z",
                },
            ),
            (
                "https://api.github.com/users/ThiagoCodecovTeam",
                {
                    "login": "ThiagoCodecovTeam",
                    "id": 57222756,
                    "node_id": "MDEyOk9yZ2FuaXphdGlvbjU3MjIyNzU2",
                    "avatar_url": "https://avatars0.githubusercontent.com/u/57222756?v=4",
                    "gravatar_id": "",
                    "url": "https://api.github.com/users/ThiagoCodecovTeam",
                    "html_url": "https://github.com/ThiagoCodecovTeam",
                    "followers_url": "https://api.github.com/users/ThiagoCodecovTeam/followers",
                    "following_url": "https://api.github.com/users/ThiagoCodecovTeam/following{/other_user}",
                    "gists_url": "https://api.github.com/users/ThiagoCodecovTeam/gists{/gist_id}",
                    "starred_url": "https://api.github.com/users/ThiagoCodecovTeam/starred{/owner}{/repo}",
                    "subscriptions_url": "https://api.github.com/users/ThiagoCodecovTeam/subscriptions",
                    "organizations_url": "https://api.github.com/users/ThiagoCodecovTeam/orgs",
                    "repos_url": "https://api.github.com/users/ThiagoCodecovTeam/repos",
                    "events_url": "https://api.github.com/users/ThiagoCodecovTeam/events{/privacy}",
                    "received_events_url": "https://api.github.com/users/ThiagoCodecovTeam/received_events",
                    "type": "Organization",
                    "site_admin": False,
                    "name": None,
                    "company": None,
                    "blog": "",
                    "location": None,
                    "email": None,
                    "hireable": None,
                    "bio": None,
                    "twitter_username": None,
                    "public_repos": 0,
                    "public_gists": 0,
                    "followers": 0,
                    "following": 0,
                    "created_at": "2019-10-31T13:07:24Z",
                    "updated_at": "2019-10-31T13:07:24Z",
                },
            ),
        ]
        for url, data in team_dicts:
            respx_vcr.get(url=url,).respond(
                status_code=200,
                json=data,
                headers={"Content-Type": "application/json; charset=utf-8"},
            )
        expected_result = [
            {"email": None, "id": "8226999", "name": "codecov", "username": "codecov",},
            {
                "email": None,
                "id": "57222756",
                "name": "ThiagoCodecovTeam",
                "username": "ThiagoCodecovTeam",
            },
        ]
        res = await valid_handler.list_teams()
        assert res == expected_result
        assert mocked_response.called is True

    @pytest.mark.asyncio
    async def test_update_check_run_no_url(self, valid_handler):
        with respx.mock:
            mocked_response = respx.patch(
                url="https://api.github.com/repos/ThiagoCodecov/example-python/check-runs/1256232357",
                json={"conclusion": "success", "status": "completed", "output": None},
            ).mock(
                return_value=httpx.Response(
                    status_code=200,
                    # response doesn't matter here
                    json={},
                    headers={"Content-Type": "application/json; charset=utf-8"},
                )
            )

            res = await valid_handler.update_check_run(1256232357, "success")

        assert mocked_response.call_count == 1

    @pytest.mark.asyncio
    async def test_update_check_run_url(self, valid_handler):
        url = "https://app.codecov.io/gh/codecov/example-python/compare/1?src=pr"
        with respx.mock:
            mocked_response = respx.patch(
                url="https://api.github.com/repos/ThiagoCodecov/example-python/check-runs/1256232357",
                json={
                    "conclusion": "success",
                    "status": "completed",
                    "output": None,
                    "details_url": "https://app.codecov.io/gh/codecov/example-python/compare/1?src=pr",
                },
            ).mock(
                return_value=httpx.Response(
                    status_code=200,
                    # response doesn't matter here
                    json={},
                    headers={"Content-Type": "application/json; charset=utf-8"},
                )
            )
            res = await valid_handler.update_check_run(1256232357, "success", url=url)
        assert mocked_response.call_count == 1
