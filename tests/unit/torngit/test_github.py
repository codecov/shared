import asyncio
import datetime
import pickle
from typing import Dict
from urllib.parse import parse_qs, parse_qsl, urlparse

import httpx
import pytest
import respx
from mock import MagicMock
from prometheus_client import REGISTRY

from shared.torngit.base import TokenType
from shared.torngit.exceptions import (
    TorngitClientError,
    TorngitClientGeneralError,
    TorngitMisconfiguredCredentials,
    TorngitObjectNotFoundError,
    TorngitRateLimitError,
    TorngitRefreshTokenFailedError,
    TorngitServer5xxCodeError,
    TorngitServerUnreachableError,
    TorngitUnauthorizedError,
)
from shared.torngit.github import Github
from shared.torngit.github import log as gh_log
from shared.typings.torngit import GithubInstallationInfo


@pytest.fixture
def respx_vcr():
    with respx.mock as v:
        yield v


@pytest.fixture
def valid_handler():
    return Github(
        repo=dict(name="example-python"),
        owner=dict(username="ThiagoCodecov"),
        token=dict(key="some_key", refresh_token="refresh_token", installation_id=0),
        oauth_consumer_token=dict(
            key="client_id",
            secret="client_secret",
        ),
    )


@pytest.fixture
def ghapp_handler():
    return Github(
        repo=dict(name="example-python", using_integration=True),
        owner=dict(username="codecov-e2e", integration_id=10000),
        token=dict(key="integration_token", installation_id=1111),
        oauth_consumer_token=dict(
            key="client_id",
            secret="client_secret",
            refresh_token="refresh_token",
        ),
    )


# Github needs a refresh_token callback function to try and refresh the token
# so we can add valid_handler._on_token_refresh = token_refresh_fake_callback
# to the tests that we want to see if Github refreshes the tokens
# other tests won't retry to refresh (cause the handlers dont have callbacks by default)
async def token_refresh_fake_callback(new_token: Dict) -> None:
    pass


class TestUnitGithub(object):
    @pytest.mark.asyncio
    async def test_api_client_error_unreachable(self, valid_handler, mocker):
        client = mocker.MagicMock(
            request=mocker.AsyncMock(return_value=mocker.MagicMock(status_code=599))
        )
        mock_refresh = mocker.patch.object(Github, "refresh_token")
        method = "GET"
        url = "random_url"
        with pytest.raises(TorngitServerUnreachableError):
            await valid_handler.api(client, method, url)
        assert mock_refresh.call_count == 0

    @pytest.mark.asyncio
    async def test_api_client_error_unauthorized(self, valid_handler, mocker):
        client = mocker.MagicMock(
            request=mocker.AsyncMock(return_value=mocker.MagicMock(status_code=401))
        )
        mock_refresh = mocker.patch.object(Github, "refresh_token")
        valid_handler._on_token_refresh = token_refresh_fake_callback
        method = "GET"
        url = "https://api.github.com/some_endpoint"
        assert callable(valid_handler._on_token_refresh)
        with pytest.raises(TorngitUnauthorizedError):
            await valid_handler.api(client, method, url)
        assert mock_refresh.call_count == 1

    @pytest.mark.parametrize(
        "status_code, error_message", [(403, "Forbidden"), (429, "Too Many Requests")]
    )
    @pytest.mark.asyncio
    async def test_api_client_error_ratelimit_reached_429(
        self, status_code, error_message
    ):
        with respx.mock:
            my_route = respx.get("https://api.github.com/endpoint").mock(
                return_value=httpx.Response(
                    status_code=status_code,
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
            assert (
                excinfo.value.message == f"Github API rate limit error: {error_message}"
            )
            assert excinfo.value.reset == "1350085394"

    @pytest.mark.parametrize("status_code", [403, 429])
    @pytest.mark.asyncio
    async def test_api_client_error_ratelimit_missing_header(self, status_code):
        with respx.mock:
            my_route = respx.get("https://api.github.com/endpoint").mock(
                return_value=httpx.Response(
                    status_code=status_code,
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
                client, "get", "/repos/%s/branches" % valid_handler.slug, per_page=100
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
        assert len(args) == 2
        built_url = args[1]
        parsed_url = urlparse(built_url)
        assert parsed_url.scheme == "https"
        assert parsed_url.netloc == "api.github.com"
        assert parsed_url.path == url
        assert parsed_url.params == ""
        assert parsed_url.fragment == ""
        query = dict(parse_qsl(parsed_url.query, keep_blank_values=True))
        assert query["qparam1"] == query_params["qparam1"]
        assert query["qparam2"] == query_params["qparam2"]

    @pytest.mark.asyncio
    async def test_api_client_change_api_host(
        self, valid_handler, mocker, mock_configuration
    ):
        mock_host = "legit-github"
        mock_configuration._params["github"] = {
            "api_url": "https://" + mock_host,
            "api_host_override": "api.github.com",
        }
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
        assert kwargs.get("headers") is not None
        assert kwargs.get("headers").get("Host") == "api.github.com"
        assert len(args) == 2
        built_url = args[1]
        parsed_url = urlparse(built_url)
        assert parsed_url.scheme == "https"
        assert parsed_url.netloc == mock_host
        assert parsed_url.path == url
        assert parsed_url.params == ""
        assert parsed_url.fragment == ""

    @pytest.mark.asyncio
    async def test_make_http_call_change_host(
        self, valid_handler, mocker, mock_configuration
    ):
        mock_host = "legit-github"
        mock_configuration._params["github"] = {
            "url": "https://" + mock_host,
            "host_override": "github.com",
        }
        client = mocker.MagicMock(
            request=mocker.AsyncMock(
                return_value=mocker.MagicMock(text="kowabunga", status_code=200)
            )
        )
        method = "GET"
        url = f"https://{mock_host}/random_url"
        query_params = {"qparam1": "a param", "qparam2": "another param"}
        await valid_handler.make_http_call(client, method, url, **query_params)
        assert client.request.call_count == 1
        args, kwargs = client.request.call_args
        assert kwargs.get("headers") is not None
        assert kwargs.get("headers").get("Host") == "github.com"
        assert len(args) == 2
        built_url = args[1]
        parsed_url = urlparse(built_url)
        assert parsed_url.scheme == "https"
        assert parsed_url.netloc == mock_host
        assert parsed_url.path == "/random_url"
        assert parsed_url.params == ""
        assert parsed_url.fragment == ""

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
        mock_refresh = mocker.patch.object(Github, "refresh_token")
        valid_handler._on_token_refresh = token_refresh_fake_callback
        method = "GET"
        url = "https://api.github.com/some_endpoint"
        res = await valid_handler.api(client, method, url, statuses_to_retry=[401])
        assert res == "FOUND"
        assert mock_refresh.call_count == 1

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
        mock_refresh = mocker.patch.object(Github, "refresh_token")
        valid_handler._on_token_refresh = token_refresh_fake_callback
        method = "GET"
        url = "https://api.github.com/some_endpoint"
        res = await valid_handler.api(client, method, url, statuses_to_retry=[401])
        assert res == "FOUND"
        assert mock_refresh.call_count == 1

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
        mock_refresh = mocker.patch.object(Github, "refresh_token")
        method = "GET"
        url = "https://api.github.com/some_endpoint"
        with pytest.raises(TorngitClientError):
            await valid_handler.api(client, method, url, statuses_to_retry=[401])
        # Doesn't try to refresh because there's no on_token_refresh callback function
        assert mock_refresh.call_count == 0

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
                    content="\xc4pple".encode("latin-1"),
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
            assert res == "\xc4pple".encode("latin-1").decode("utf-8", errors="replace")

    @pytest.mark.asyncio
    async def test_find_pull_request_success(self, mocker):
        before = REGISTRY.get_sample_value(
            "git_provider_api_calls_github_total",
            labels={"endpoint": "find_pull_request"},
        )
        handler = Github(
            repo=dict(name="repo_name"),
            owner=dict(username="username"),
            token=dict(key="aaaaa"),
        )
        commit_sha = "some_commit_sha"
        mock_log = mocker.patch.object(
            gh_log, "warning"
        )  # Used to check if the log message is fired because there are 2 PRs with the commit
        with respx.mock:
            respx.get(
                url=f"https://api.github.com/repos/{handler.slug}/commits/{commit_sha}/pulls"
            ).mock(
                return_value=httpx.Response(
                    status_code=200,
                    # Response for pulls endpoint returns a list directly
                    json=[
                        {
                            "id": 575148805,
                            "node_id": "MDExOlB1bFkSZXF1ZXN0MzgzMzQ4Nzc1",
                            "number": 13,
                            "title": "feat/other-pr",
                            "labels": [],
                            "state": "closed",
                            "locked": True,
                        },
                        {
                            "id": 575148804,
                            "node_id": "MDExOlB1bGxSZXF1ZXN0MzgzMzQ4Nzc1",
                            "number": 18,
                            "title": "Thiago/base no base",
                            "labels": [],
                            "state": "open",
                            "locked": False,
                        },
                        {
                            "id": 575148804,
                            "node_id": "MDExOlB1bGxSZXF1ZXN0MzgzMzQ4Nzc1",
                            "number": 19,
                            "title": "Thiago/base no base",
                            "labels": [],
                            "state": "open",
                            "locked": False,
                        },
                        {
                            "id": 575148805,
                            "node_id": "MDExOlB1bFkSZXF1ZXN0MzgzMzQ4Nzc1",
                            "number": 22,
                            "title": "feat/other-pr",
                            "labels": [],
                            "state": "closed",
                            "locked": True,
                        },
                    ],
                    headers={"Content-Type": "application/json; charset=utf-8"},
                )
            )

            res = await handler.find_pull_request(commit=commit_sha)
            assert res == 18
            mock_log.assert_called_with(
                "Commit is referenced in multiple PRs.",
                extra=dict(
                    prs=[18, 19],
                    commit="some_commit_sha",
                    slug="username/repo_name",
                    state="open",
                ),
            )
            after = REGISTRY.get_sample_value(
                "git_provider_api_calls_github_total",
                labels={"endpoint": "find_pull_request"},
            )
            assert after - before == 1

    @pytest.mark.asyncio
    async def test_find_pr_by_pulls_failfast_if_no_commit(self, mocker):
        before = REGISTRY.get_sample_value(
            "git_provider_api_calls_github_total",
            labels={"endpoint": "find_pull_request"},
        )
        handler = Github(
            repo=dict(name="repo_name"),
            owner=dict(username="username"),
            token=dict(key="aaaaa"),
        )
        res = await handler.find_pull_request(commit=None)
        assert res is None
        after = REGISTRY.get_sample_value(
            "git_provider_api_calls_github_total",
            labels={"endpoint": "find_pull_request"},
        )
        assert after - before == 0

    @pytest.mark.asyncio
    async def test_find_pr_by_pulls_failfast_if_no_slug(self, mocker):
        before = REGISTRY.get_sample_value(
            "git_provider_api_calls_github_total",
            labels={"endpoint": "find_pull_request"},
        )
        handler = Github(
            owner=dict(username="username"),
            token=dict(key="aaaaa"),
        )
        commit_sha = "some_commit_sha"
        assert handler.slug is None
        res = await handler.find_pull_request(None, commit_sha, None)
        assert res is None
        after = REGISTRY.get_sample_value(
            "git_provider_api_calls_github_total",
            labels={"endpoint": "find_pull_request"},
        )
        assert after - before == 0

    @pytest.mark.asyncio
    async def test_find_pr_by_pulls_raise_exp_if_not_422(self, mocker):
        before = REGISTRY.get_sample_value(
            "git_provider_api_calls_github_total",
            labels={"endpoint": "find_pull_request"},
        )
        handler = Github(
            repo=dict(name="repo_name"),
            owner=dict(username="username"),
            token=dict(key="aaaaa"),
        )
        commit_sha = "some_commit_sha"
        with respx.mock:
            respx.get(
                url=f"https://api.github.com/repos/{handler.slug}/commits/{commit_sha}/pulls"
            ).mock(
                return_value=httpx.Response(
                    status_code=425,
                    # Response for pulls endpoint returns a list directly
                    json={"reason_phrase": "Some message"},
                    headers={"Content-Type": "application/json; charset=utf-8"},
                )
            )
            token = handler.get_token_by_type(TokenType.read)
            with pytest.raises(TorngitClientGeneralError):
                await handler.find_pull_request(commit=commit_sha, token=token)
            after = REGISTRY.get_sample_value(
                "git_provider_api_calls_github_total",
                labels={"endpoint": "find_pull_request"},
            )
            assert after - before == 1

    @pytest.mark.asyncio
    async def test_distance_in_commits(self, mocker):
        before = REGISTRY.get_sample_value(
            "git_provider_api_calls_github_total",
            labels={"endpoint": "get_distance_in_commits"},
        )
        handler = Github(
            repo=dict(name="repo_name"),
            owner=dict(username="username"),
            token=dict(key="aaaaa"),
        )
        base_commit_sha = "some_commit_sha"
        repos_default_branch = "branch"
        with respx.mock:
            respx.get(
                url=f"https://api.github.com/repos/{handler.slug}/compare/{repos_default_branch}...{base_commit_sha}"
            ).mock(
                return_value=httpx.Response(
                    status_code=200,
                    json={
                        "status": "behind",
                        "ahead_by": 0,
                        "behind_by": 10,
                        "total_commits": 0,
                        "commits": [],
                        "files": [],
                        "base_commit": {
                            "sha": "c63a6b7c0dbc9e04a3bc8c109519615098325e41",
                        },
                    },
                    headers={"Content-Type": "application/json; charset=utf-8"},
                )
            )
            expected_result = {
                "behind_by": 10,
                "behind_by_commit": "c63a6b7c0dbc9e04a3bc8c109519615098325e41",
                "status": "behind",
                "ahead_by": 0,
            }
            res = await handler.get_distance_in_commits(
                repos_default_branch, base_commit_sha
            )
            assert res == expected_result
            after = REGISTRY.get_sample_value(
                "git_provider_api_calls_github_total",
                labels={"endpoint": "get_distance_in_commits"},
            )
            assert after - before == 1

    @pytest.mark.asyncio
    async def test_null_distance_in_commits(self, mocker):
        before = REGISTRY.get_sample_value(
            "git_provider_api_calls_github_total",
            labels={"endpoint": "get_distance_in_commits"},
        )
        handler = Github(
            repo=dict(name="repo_name"),
            owner=dict(username="username"),
            token=dict(key="aaaaa"),
        )
        base_commit_sha = "some_commit_sha"
        repos_default_branch = "branch"
        with respx.mock:
            respx.get(
                url=f"https://api.github.com/repos/{handler.slug}/compare/{repos_default_branch}...{base_commit_sha}"
            ).mock(
                return_value=httpx.Response(
                    status_code=200,
                    json={
                        "status": "behind",
                        "ahead_by": 0,
                        "behind_by": 0,
                        "total_commits": 0,
                        "commits": [],
                        "files": [],
                    },
                    headers={"Content-Type": "application/json; charset=utf-8"},
                )
            )
            expected_result = {
                "behind_by": None,
                "behind_by_commit": None,
                "status": "behind",
                "ahead_by": 0,
            }
            res = await handler.get_distance_in_commits(
                repos_default_branch, base_commit_sha
            )
            assert res == expected_result
            after = REGISTRY.get_sample_value(
                "git_provider_api_calls_github_total",
                labels={"endpoint": "get_distance_in_commits"},
            )
            assert after - before == 1

    @pytest.mark.asyncio
    async def test_post_comment(self, respx_vcr, valid_handler):
        before = REGISTRY.get_sample_value(
            "git_provider_api_calls_github_total", labels={"endpoint": "post_comment"}
        )
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
        after = REGISTRY.get_sample_value(
            "git_provider_api_calls_github_total", labels={"endpoint": "post_comment"}
        )
        assert after - before == 1

    @pytest.mark.asyncio
    async def test_list_teams(self, valid_handler, respx_vcr):
        before_first_call = REGISTRY.get_sample_value(
            "git_provider_api_calls_github_total", labels={"endpoint": "list_teams"}
        )
        before_second_call = REGISTRY.get_sample_value(
            "git_provider_api_calls_github_total",
            labels={"endpoint": "list_teams_org_name"},
        )
        mocked_response = respx_vcr.get(
            url="https://api.github.com/user/memberships/orgs?state=active&page=1"
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
            respx_vcr.get(url=url).respond(
                status_code=200,
                json=data,
                headers={"Content-Type": "application/json; charset=utf-8"},
            )
        expected_result = [
            {"email": None, "id": "8226999", "name": "codecov", "username": "codecov"},
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
        after_first_call = REGISTRY.get_sample_value(
            "git_provider_api_calls_github_total", labels={"endpoint": "list_teams"}
        )
        assert after_first_call - before_first_call == 1
        after_second_call = REGISTRY.get_sample_value(
            "git_provider_api_calls_github_total",
            labels={"endpoint": "list_teams_org_name"},
        )
        assert after_second_call - before_second_call == 2  # len(mocked_response[json]

    @pytest.mark.asyncio
    async def test_list_team_with_org_response_404(self, valid_handler, respx_vcr):
        before_first_call = REGISTRY.get_sample_value(
            "git_provider_api_calls_github_total", labels={"endpoint": "list_teams"}
        )
        before_second_call = REGISTRY.get_sample_value(
            "git_provider_api_calls_github_total",
            labels={"endpoint": "list_teams_org_name"},
        )
        mocked_response = respx_vcr.get(
            url="https://api.github.com/user/memberships/orgs?state=active&page=1"
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
                }
            ],
            headers={"Content-Type": "application/json; charset=utf-8"},
        )

        respx_vcr.get(url="https://api.github.com/users/codecov").respond(
            status_code=404,
            json={},
            headers={"Content-Type": "application/json; charset=utf-8"},
        )
        res = await valid_handler.list_teams()
        assert res == []
        assert mocked_response.called is True
        after_first_call = REGISTRY.get_sample_value(
            "git_provider_api_calls_github_total", labels={"endpoint": "list_teams"}
        )
        assert after_first_call - before_first_call == 1
        after_second_call = REGISTRY.get_sample_value(
            "git_provider_api_calls_github_total",
            labels={"endpoint": "list_teams_org_name"},
        )
        assert after_second_call - before_second_call == 1  # len(mocked_response[json]

    @pytest.mark.asyncio
    async def test_update_check_run_no_url(self, valid_handler):
        before = REGISTRY.get_sample_value(
            "git_provider_api_calls_github_total",
            labels={"endpoint": "update_check_run"},
        )
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
        after = REGISTRY.get_sample_value(
            "git_provider_api_calls_github_total",
            labels={"endpoint": "update_check_run"},
        )
        assert after - before == 1

    @pytest.mark.asyncio
    async def test_update_check_run_url(self, valid_handler):
        before = REGISTRY.get_sample_value(
            "git_provider_api_calls_github_total",
            labels={"endpoint": "update_check_run"},
        )
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
        after = REGISTRY.get_sample_value(
            "git_provider_api_calls_github_total",
            labels={"endpoint": "update_check_run"},
        )
        assert after - before == 1

    @pytest.mark.asyncio
    async def test_update_check_run_url_fallback(self, mocker):
        mock_redis_conn = MagicMock(name="fake_redis")
        mocker.patch(
            "shared.torngit.github.get_redis_connection", return_value=mock_redis_conn
        )
        mock_get_token = mocker.patch(
            "shared.torngit.github.get_github_integration_token",
            return_value="fallback_token",
        )

        handler = Github(
            repo=dict(name="example-python"),
            owner=dict(username="ThiagoCodecov"),
            token=dict(key="some_key", refresh_token="refresh_token"),
            oauth_consumer_token=dict(
                key="client_id",
                secret="client_secret",
            ),
            installation=GithubInstallationInfo(
                installation_id=1500,
            ),
            fallback_installations=[
                {"installation_id": 12342, "app_id": 1200, "pem_path": "some_path"}
            ],
        )

        url = "https://app.codecov.io/gh/codecov/example-python/compare/1?src=pr"
        five_min_from_now = datetime.datetime.now(
            datetime.timezone.utc
        ) + datetime.timedelta(minutes=5)
        timestamp = int(five_min_from_now.timestamp())
        assert (
            timestamp - int(datetime.datetime.now(datetime.timezone.utc).timestamp())
            == 300
        )
        with respx.mock:
            mocked_response = respx.patch(
                "https://api.github.com/repos/ThiagoCodecov/example-python/check-runs/1256232357",
                json={
                    "conclusion": "success",
                    "status": "completed",
                    "output": None,
                    "details_url": "https://app.codecov.io/gh/codecov/example-python/compare/1?src=pr",
                },
                headers__contains={"Authorization": "token some_key"},
            ).mock(
                return_value=httpx.Response(
                    status_code=429,
                    headers={
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": str(timestamp),
                    },
                )
            )
            mocked_response_fallback = respx.patch(
                url="https://api.github.com/repos/ThiagoCodecov/example-python/check-runs/1256232357",
                json={
                    "conclusion": "success",
                    "status": "completed",
                    "output": None,
                    "details_url": "https://app.codecov.io/gh/codecov/example-python/compare/1?src=pr",
                },
                headers__contains={"Authorization": "token fallback_token"},
            ).mock(
                return_value=httpx.Response(
                    status_code=200,
                    # response doesn't matter here
                    json={},
                    headers={"Content-Type": "application/json; charset=utf-8"},
                )
            )
            res = await handler.update_check_run(1256232357, "success", url=url)
        assert mocked_response.call_count == 1
        assert mocked_response_fallback.call_count == 1
        # The installation from the original token (rate limited) is marked so
        mock_redis_conn.set.assert_called_with(
            name="rate_limited_installations_default_app_1500", value=True, ex=300
        )
        mock_get_token.assert_called_with(
            "github", 12342, app_id=1200, pem_path="some_path"
        )
        # The token in the GitHub instance is updated for subsequent requests
        assert handler._token == {
            "key": "fallback_token",
        }
        assert handler.data["fallback_installations"] == []

    @pytest.mark.asyncio
    async def test_get_general_exception_pickle(self, valid_handler, mocker):
        before = REGISTRY.get_sample_value(
            "git_provider_api_calls_github_total",
            labels={"endpoint": "get_pull_requests"},
        )
        mock_refresh = mocker.patch.object(Github, "refresh_token")
        valid_handler._on_token_refresh = token_refresh_fake_callback
        with respx.mock:
            mocked_response = respx.get(
                url="https://api.github.com/repos/ThiagoCodecov/example-python/pulls?page=1&per_page=25&state=open"
            ).mock(
                return_value=httpx.Response(
                    status_code=404,
                    # response doesn't matter here
                    json={},
                    headers={"Content-Type": "application/json; charset=utf-8"},
                )
            )
            with pytest.raises(TorngitClientGeneralError) as ex:
                await valid_handler.get_pull_requests()
            error = ex.value
            text = pickle.dumps(error)
            renegerated_error = pickle.loads(text)
            assert isinstance(renegerated_error, TorngitClientGeneralError)
            assert renegerated_error.code == error.code

        assert mocked_response.call_count == 2
        assert mock_refresh.call_count == 1
        after = REGISTRY.get_sample_value(
            "git_provider_api_calls_github_total",
            labels={"endpoint": "get_pull_requests"},
        )
        assert after - before == 1

    @pytest.mark.asyncio
    async def test_api_no_token(self):
        c = Github()
        with pytest.raises(TorngitMisconfiguredCredentials):
            await c.api()

    @pytest.mark.asyncio
    async def test_paginated_api_no_token(self, mocker):
        c = Github()
        with pytest.raises(TorngitMisconfiguredCredentials):
            async for page in c.paginated_api_generator(
                mocker.MagicMock(), mocker.MagicMock(), mocker.MagicMock()
            ):
                pass

    @pytest.mark.asyncio
    async def test_list_webhook_deliveries(self, ghapp_handler):
        before = REGISTRY.get_sample_value(
            "git_provider_api_calls_github_total",
            labels={"endpoint": "list_webhook_deliveries"},
        )

        def side_effect(request):
            assert request.headers.get("Accept") == "application/vnd.github+json"
            assert (
                request.headers.get("Authorization")
                == f"Bearer {ghapp_handler.token['key']}"
            )

            return httpx.Response(
                status_code=200,
                json=[
                    {
                        "id": 17324040107,
                        "guid": "53c93580-7a6e-11ed-96c9-5e1ce3e5574e",  # this value is the same accross redeliveries
                        "delivered_at": "2022-12-12T22:42:59Z",
                        "redelivery": False,
                        "duration": 0.37,
                        "status": "OK",
                        "status_code": 200,
                        "event": "installation_repositories",  # when you add / remove repos from installation
                        "action": "added",
                        "installation_id": None,
                        "repository_id": None,
                        "url": "",
                    },
                    {
                        "id": 17324018336,
                        "guid": "40d7f830-7a6e-11ed-8b90-0777e88b1858",
                        "delivered_at": "2022-12-12T22:42:30Z",
                        "redelivery": False,
                        "duration": 2.31,
                        "status": "OK",
                        "status_code": 200,
                        "event": "installation_repositories",
                        "action": "removed",
                        "installation_id": None,
                        "repository_id": None,
                        "url": "",
                    },
                    {
                        "id": 17323292984,
                        "guid": "0498e8e0-7a6c-11ed-8834-c5eb5a4b102a",
                        "delivered_at": "2022-12-12T22:26:28Z",
                        "redelivery": False,
                        "duration": 0.69,
                        "status": "Invalid HTTP Response: 400",
                        "status_code": 400,
                        "event": "installation",  # A new installation
                        "action": "created",
                        "installation_id": None,
                        "repository_id": None,
                        "url": "",
                    },
                    {
                        "id": 17323228732,
                        "guid": "d41fa780-7a6b-11ed-8890-0619085a3f97",
                        "delivered_at": "2022-12-12T22:25:07Z",
                        "redelivery": False,
                        "duration": 0.74,
                        "status": "Invalid HTTP Response: 400",
                        "status_code": 400,
                        "event": "installation",
                        "action": "deleted",
                        "installation_id": None,
                        "repository_id": None,
                        "url": "",
                    },
                ],
                headers={"Content-Type": "application/json; charset=utf-8"},
            )

        with respx.mock:
            mocked_response = respx.get(
                url="https://api.github.com/app/hook/deliveries?per_page=50",
            ).mock(side_effect=side_effect)
            async for res in ghapp_handler.list_webhook_deliveries():
                assert len(res) == 4
        assert mocked_response.call_count == 1
        after = REGISTRY.get_sample_value(
            "git_provider_api_calls_github_total",
            labels={"endpoint": "list_webhook_deliveries"},
        )
        assert after - before == 1

    @pytest.mark.asyncio
    async def test_list_webhook_deliveries_multiple_pages(self, ghapp_handler):
        before = REGISTRY.get_sample_value(
            "git_provider_api_calls_github_total",
            labels={"endpoint": "list_webhook_deliveries"},
        )
        with respx.mock:
            mocked_response_1 = respx.get(
                url="https://api.github.com/app/hook/deliveries?per_page=50"
            ).mock(
                return_value=httpx.Response(
                    status_code=200,
                    headers=dict(
                        link='<https://api.github.com/app/hook/deliveries?per_page=50&cursor=v1_17323292984>; rel="next"'
                    ),
                    json=[
                        {
                            "id": 17324040107,
                            "guid": "53c93580-7a6e-11ed-96c9-5e1ce3e5574e",  # this value is the same accross redeliveries
                            "delivered_at": "2022-12-12T22:42:59Z",
                            "redelivery": False,
                            "duration": 0.37,
                            "status": "OK",
                            "status_code": 200,
                            "event": "installation_repositories",  # when you add / remove repos from installation
                            "action": "added",
                            "installation_id": None,
                            "repository_id": None,
                            "url": "",
                        },
                        {
                            "id": 17324018336,
                            "guid": "40d7f830-7a6e-11ed-8b90-0777e88b1858",
                            "delivered_at": "2022-12-12T22:42:30Z",
                            "redelivery": False,
                            "duration": 2.31,
                            "status": "OK",
                            "status_code": 200,
                            "event": "installation_repositories",
                            "action": "removed",
                            "installation_id": None,
                            "repository_id": None,
                            "url": "",
                        },
                    ],
                )
            )
            mocked_response_2 = respx.get(
                url="https://api.github.com/app/hook/deliveries?per_page=50&cursor=v1_17323292984"
            ).mock(
                return_value=httpx.Response(
                    status_code=200,
                    json=[
                        {
                            "id": 17323292984,
                            "guid": "0498e8e0-7a6c-11ed-8834-c5eb5a4b102a",
                            "delivered_at": "2022-12-12T22:26:28Z",
                            "redelivery": False,
                            "duration": 0.69,
                            "status": "Invalid HTTP Response: 400",
                            "status_code": 400,
                            "event": "installation",  # A new installation
                            "action": "created",
                            "installation_id": None,
                            "repository_id": None,
                            "url": "",
                        },
                        {
                            "id": 17323228732,
                            "guid": "d41fa780-7a6b-11ed-8890-0619085a3f97",
                            "delivered_at": "2022-12-12T22:25:07Z",
                            "redelivery": False,
                            "duration": 0.74,
                            "status": "Invalid HTTP Response: 400",
                            "status_code": 400,
                            "event": "installation",
                            "action": "deleted",
                            "installation_id": None,
                            "repository_id": None,
                            "url": "",
                        },
                    ],
                )
            )
            aggregate_res = []
            async for res in ghapp_handler.list_webhook_deliveries():
                assert len(res) == 2
                aggregate_res += res
        assert len(aggregate_res) == 4
        assert mocked_response_1.call_count == 1
        assert mocked_response_2.call_count == 1
        after = REGISTRY.get_sample_value(
            "git_provider_api_calls_github_total",
            labels={"endpoint": "list_webhook_deliveries"},
        )
        assert after - before == 2

    @pytest.mark.asyncio
    async def test_webhook_redelivery_success(self, ghapp_handler):
        delivery_id = 17323228732
        before = REGISTRY.get_sample_value(
            "git_provider_api_calls_github_total",
            labels={"endpoint": "request_webhook_redelivery"},
        )

        def side_effect(request):
            assert request.headers.get("Accept") == "application/vnd.github+json"
            assert (
                request.headers.get("Authorization")
                == f"Bearer {ghapp_handler.token['key']}"
            )
            assert request.method == "POST"
            return httpx.Response(
                status_code=202, headers={"Content-Type": "applicaiton/json"}
            )

        with respx.mock:
            mocked_response = respx.post(
                url=f"https://api.github.com/app/hook/deliveries/{delivery_id}/attempts"
            ).mock(side_effect=side_effect)
            ans = await ghapp_handler.request_webhook_redelivery(delivery_id)
            assert ans is True
        assert mocked_response.call_count == 1
        after = REGISTRY.get_sample_value(
            "git_provider_api_calls_github_total",
            labels={"endpoint": "request_webhook_redelivery"},
        )
        assert after - before == 1

    @pytest.mark.asyncio
    async def test_webhook_redelivery_fail(self, ghapp_handler):
        delivery_id = 17323228732
        before = REGISTRY.get_sample_value(
            "git_provider_api_calls_github_total",
            labels={"endpoint": "request_webhook_redelivery"},
        )
        with respx.mock:
            mocked_response = respx.post(
                url=f"https://api.github.com/app/hook/deliveries/{delivery_id}/attempts"
            ).mock(
                return_value=httpx.Response(
                    status_code=422, headers={"Content-Type": "applicaiton/json"}
                ),
            )
            ans = await ghapp_handler.request_webhook_redelivery(delivery_id)
            assert ans is False
        assert mocked_response.call_count == 1
        after = REGISTRY.get_sample_value(
            "git_provider_api_calls_github_total",
            labels={"endpoint": "request_webhook_redelivery"},
        )
        assert after - before == 1

    @pytest.mark.asyncio
    async def test_get_pull_request_files_404(self, mocker):
        before = REGISTRY.get_sample_value(
            "git_provider_api_calls_github_total",
            labels={"endpoint": "get_pull_request_files"},
        )
        mock_refresh = mocker.patch.object(Github, "refresh_token")
        with respx.mock:
            my_route = respx.get(
                "https://api.github.com/repos/codecove2e/example-python/pulls/4/files"
            ).mock(
                return_value=httpx.Response(
                    status_code=404,
                    headers={
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": "1350085394",
                    },
                )
            )
            handler = Github(
                repo=dict(name="example-python"),
                owner=dict(username="codecove2e"),
                token=dict(key=10 * "a280"),
            )
            handler._on_token_refresh = token_refresh_fake_callback
            with pytest.raises(TorngitObjectNotFoundError) as excinfo:
                res = await handler.get_pull_request_files(4)
            assert excinfo.value.code == 404
            assert excinfo.value.message == "PR with id 4 does not exist"
        assert mock_refresh.call_count == 1
        after = REGISTRY.get_sample_value(
            "git_provider_api_calls_github_total",
            labels={"endpoint": "get_pull_request_files"},
        )
        assert after - before == 1

    @pytest.mark.asyncio
    async def test_get_pull_request_files_403(self):
        before = REGISTRY.get_sample_value(
            "git_provider_api_calls_github_total",
            labels={"endpoint": "get_pull_request_files"},
        )
        with respx.mock:
            my_route = respx.get(
                "https://api.github.com/repos/codecove2e/example-python/pulls/4/files"
            ).mock(
                return_value=httpx.Response(
                    status_code=403,
                    headers={
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": "1350085394",
                    },
                )
            )
            handler = Github(
                repo=dict(name="example-python"),
                owner=dict(username="codecove2e"),
                token=dict(key=10 * "a280"),
            )
            with pytest.raises(TorngitClientError) as excinfo:
                res = await handler.get_pull_request_files(4)
            assert excinfo.value.code == 403
            assert excinfo.value.message == "Github API rate limit error: Forbidden"
            after = REGISTRY.get_sample_value(
                "git_provider_api_calls_github_total",
                labels={"endpoint": "get_pull_request_files"},
            )
            assert after - before == 1

    @pytest.mark.asyncio
    async def test_get_pull_request_files_403_secondary_limit(self):
        before = REGISTRY.get_sample_value(
            "git_provider_api_calls_github_total",
            labels={"endpoint": "get_pull_request_files"},
        )
        with respx.mock:
            my_route = respx.get(
                "https://api.github.com/repos/codecove2e/example-python/pulls/4/files"
            ).mock(
                return_value=httpx.Response(
                    status_code=403,
                    headers={
                        "Retry-After": "60",
                    },
                )
            )
            handler = Github(
                repo=dict(name="example-python"),
                owner=dict(username="codecove2e"),
                token=dict(key=10 * "a280"),
            )
            with pytest.raises(TorngitRateLimitError) as excinfo:
                res = await handler.get_pull_request_files(4)
            assert excinfo.value.code == 403
            assert (
                excinfo.value.message
                == "Github API rate limit error: secondary rate limit"
            )
            assert excinfo.value.retry_after == 60
            after = REGISTRY.get_sample_value(
                "git_provider_api_calls_github_total",
                labels={"endpoint": "get_pull_request_files"},
            )
            assert after - before == 1

    @pytest.mark.asyncio
    async def test_github_refresh_fail_terminates_unavailable(
        self, mocker, valid_handler
    ):
        before = REGISTRY.get_sample_value(
            "git_provider_api_calls_github_total", labels={"endpoint": "refresh_token"}
        )
        with pytest.raises(TorngitRefreshTokenFailedError) as exp:
            with respx.mock:
                mocked_refresh = respx.post(
                    "https://github.com/login/oauth/access_token"
                ).mock(
                    return_value=httpx.Response(
                        status_code=502, content="Service unavailable try again later"
                    )
                )
                await valid_handler.refresh_token(
                    valid_handler.get_client(), "original_request_url"
                )
            assert exp.code == 555
        assert mocked_refresh.call_count == 1
        after = REGISTRY.get_sample_value(
            "git_provider_api_calls_github_total", labels={"endpoint": "refresh_token"}
        )
        assert after - before == 1

    @pytest.mark.asyncio
    async def test_github_refresh_fail_terminates_unauthorized(
        self, mocker, valid_handler
    ):
        before = REGISTRY.get_sample_value(
            "git_provider_api_calls_github_total", labels={"endpoint": "refresh_token"}
        )
        with pytest.raises(TorngitRefreshTokenFailedError) as exp:
            with respx.mock:
                mocked_refresh = respx.post(
                    "https://github.com/login/oauth/access_token"
                ).mock(
                    return_value=httpx.Response(
                        status_code=403, content='{"error": "unauthorized"}'
                    )
                )
                await valid_handler.refresh_token(
                    valid_handler.get_client(), "original_request_url"
                )
            assert exp.code == 555
        assert mocked_refresh.call_count == 1
        after = REGISTRY.get_sample_value(
            "git_provider_api_calls_github_total", labels={"endpoint": "refresh_token"}
        )
        assert after - before == 1

    @pytest.mark.asyncio
    async def test_github_refresh_fail_terminates_no_refresh_token(
        self, mocker, valid_handler
    ):
        old_token = valid_handler._token
        valid_handler._token = {"access_token": "old_token_without_refresh"}
        res = await valid_handler.refresh_token(
            valid_handler.get_client(), "original_request_url"
        )
        assert res is None
        valid_handler._token = old_token

    @pytest.mark.asyncio
    async def test_github_double_refresh(self, mocker, valid_handler):
        before = REGISTRY.get_sample_value(
            "git_provider_api_calls_github_total", labels={"endpoint": "refresh_token"}
        )

        def side_effect(request, *args, **kwargs):
            url_parts = urlparse(str(request.url))
            query = url_parts.query
            params = parse_qs(query)
            refresh_token = params["refresh_token"][0]
            if refresh_token == "refresh_token":
                return httpx.Response(
                    status_code=200,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                    text="access_token=new_access_token&token_type=bearer&refresh_token=new_refresh_token",
                )
            elif refresh_token == "new_refresh_token":
                return httpx.Response(
                    status_code=200,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                    text="access_token=newer_access_token&token_type=bearer&refresh_token=newer_refresh_token",
                )
            pytest.fail("Wrong token received")

        assert valid_handler._oauth == dict(key="client_id", secret="client_secret")

        with respx.mock:
            mocked_refresh = respx.post(
                "https://github.com/login/oauth/access_token"
            ).mock(side_effect=side_effect)
            await valid_handler.refresh_token(
                valid_handler.get_client(), "original_request_url"
            )
            assert mocked_refresh.call_count == 1
            assert valid_handler._token == dict(
                key="new_access_token", refresh_token="new_refresh_token"
            )

            await valid_handler.refresh_token(
                valid_handler.get_client(), "original_request_url"
            )
            assert mocked_refresh.call_count == 2
            assert valid_handler._token == dict(
                key="newer_access_token", refresh_token="newer_refresh_token"
            )

        # Make sure that changing the token doesn't change the _oauth
        assert valid_handler._oauth == dict(key="client_id", secret="client_secret")
        after = REGISTRY.get_sample_value(
            "git_provider_api_calls_github_total", labels={"endpoint": "refresh_token"}
        )
        assert after - before == 2

    @pytest.mark.asyncio
    async def test_github_is_student_timeout(self, ghapp_handler):
        before = REGISTRY.get_sample_value(
            "git_provider_api_calls_github_total", labels={"endpoint": "is_student"}
        )

        def side_effect(*args, **kwargs):
            raise httpx.TimeoutException("timeout")

        with respx.mock:
            mocked_route = respx.get("https://education.github.com/api/user").mock(
                side_effect=side_effect
            )
            res = await ghapp_handler.is_student()
            assert mocked_route.call_count == 1
            assert res == False
        after = REGISTRY.get_sample_value(
            "git_provider_api_calls_github_total", labels={"endpoint": "is_student"}
        )
        assert after - before == 1

    @pytest.mark.asyncio
    async def test_github_is_student_network_error(self, ghapp_handler):
        before = REGISTRY.get_sample_value(
            "git_provider_api_calls_github_total", labels={"endpoint": "is_student"}
        )

        def side_effect(*args, **kwargs):
            raise httpx.NetworkError("timeout")

        with respx.mock:
            mocked_route = respx.get("https://education.github.com/api/user").mock(
                side_effect=side_effect
            )
            res = await ghapp_handler.is_student()
            assert mocked_route.call_count == 1
            assert res == False
        after = REGISTRY.get_sample_value(
            "git_provider_api_calls_github_total", labels={"endpoint": "is_student"}
        )
        assert after - before == 1

    @pytest.mark.asyncio
    async def test_github_refresh_after_failed_request(self, mocker, valid_handler):
        before = REGISTRY.get_sample_value(
            "git_provider_api_calls_github_total", labels={"endpoint": "get_is_admin"}
        )
        before_retries = REGISTRY.get_sample_value(
            "git_provider_api_calls_github_total",
            labels={"endpoint": "make_http_call_retry"},
        )
        before_token_refresh = REGISTRY.get_sample_value(
            "git_provider_api_calls_github_total", labels={"endpoint": "refresh_token"}
        )

        def side_effect(request, *args, **kwargs):
            token = request.headers["Authorization"]
            if token == "token some_key":
                return httpx.Response(
                    status_code=401,
                    content='{"message":"Bad Request"}',
                )
            elif token == "token new_access_token":
                return httpx.Response(
                    status_code=200, json={"state": "active", "role": "admin"}
                )
            pytest.fail(f"Wrong token received ({token})")

        f = asyncio.Future()
        f.set_result(True)
        mock_refresh_callback: MagicMock = mocker.patch.object(
            valid_handler, "_on_token_refresh", create=True, return_value=f
        )
        with respx.mock:
            mocked_route = respx.get(
                "https://api.github.com/orgs/ThiagoCodecov/memberships/John%20Doe"
            ).mock(side_effect=side_effect)
            mocked_refresh = respx.post(
                "https://github.com/login/oauth/access_token"
            ).mock(
                return_value=httpx.Response(
                    status_code=200,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                    text="access_token=new_access_token&token_type=bearer&refresh_token=new_refresh_token",
                )
            )
            await valid_handler.get_is_admin(user={"username": "John Doe"})
        assert mocked_route.call_count == 2
        assert mocked_refresh.call_count == 1
        assert valid_handler._token["key"] == "new_access_token"
        assert valid_handler._token["refresh_token"] == "new_refresh_token"
        assert mock_refresh_callback.call_count == 1
        mock_refresh_callback.assert_called_with(
            {
                "key": "new_access_token",
                "refresh_token": "new_refresh_token",
            }
        )
        after = REGISTRY.get_sample_value(
            "git_provider_api_calls_github_total", labels={"endpoint": "get_is_admin"}
        )
        assert after - before == 1
        after_retries = REGISTRY.get_sample_value(
            "git_provider_api_calls_github_total",
            labels={"endpoint": "make_http_call_retry"},
        )
        assert after_retries - before_retries == 1
        after_token_refresh = REGISTRY.get_sample_value(
            "git_provider_api_calls_github_total", labels={"endpoint": "refresh_token"}
        )
        assert after_token_refresh - before_token_refresh == 1

    @pytest.mark.asyncio
    async def test__get_owner_from_nodeid(self, ghapp_handler):
        before = REGISTRY.get_sample_value(
            "git_provider_api_calls_github_total",
            labels={"endpoint": "get_owner_from_nodeid_graphql"},
        )
        with respx.mock:
            mocked_route = respx.post("https://api.github.com/graphql").mock(
                return_value=httpx.Response(
                    status_code=200,
                    headers={"Content-Type": "application/json"},
                    json={
                        "data": {
                            "node": {
                                "__typename": "Organization",
                                "name": "Codecov",
                                "login": "codecov",
                                "databaseId": 8226205,
                            },
                        }
                    },
                )
            )
            node_id = "U_kgDOBfIxWg"
            async with ghapp_handler.get_client() as client:
                res = await ghapp_handler._get_owner_from_nodeid(
                    client=client, token=MagicMock(), owner_node_id=node_id
                )
            assert res == {"username": "codecov", "service_id": 8226205}
            assert mocked_route.call_count == 1
            after = REGISTRY.get_sample_value(
                "git_provider_api_calls_github_total",
                labels={"endpoint": "get_owner_from_nodeid_graphql"},
            )
            assert after - before == 1

    @pytest.mark.asyncio
    async def test_get_repos_from_nodeids(self, ghapp_handler):
        before = REGISTRY.get_sample_value(
            "git_provider_api_calls_github_total",
            labels={"endpoint": "get_repos_from_nodeids_generator_graphql"},
        )
        before_get_owner = REGISTRY.get_sample_value(
            "git_provider_api_calls_github_total",
            labels={"endpoint": "get_owner_from_nodeid_graphql"},
        )

        # Mocking different responses from the graphQL API
        # because it all goes to the same endpoint but this test expects a 2nd call
        # with owner by node_id query
        def mock_route_side_effect(request):
            content_string = request.content.decode()
            if "query GetReposFromNodeIds" in content_string:
                return httpx.Response(
                    status_code=200,
                    json={
                        "data": {
                            "nodes": [
                                {
                                    "__typename": "Repository",
                                    "databaseId": 460565350,
                                    "name": "codecov-cli",
                                    "primaryLanguage": {"name": "Python"},
                                    "isPrivate": False,
                                    "defaultBranchRef": {"name": "main"},
                                    "owner": {
                                        "id": "MDEyOk9yZ2FuaXphdGlvbjgyMjYyMDU=",
                                        "login": "codecov",
                                    },
                                },
                                None,
                                {
                                    "__typename": "Repository",
                                    "databaseId": 665728948,
                                    "name": "worker",
                                    "primaryLanguage": {"name": "Python"},
                                    "isPrivate": False,
                                    "defaultBranchRef": {"name": "main"},
                                    "owner": {
                                        "id": "MDEyOk9yZ2FuaXphdGlvbjgyMjYyMDU=",
                                        "login": "codecov",
                                    },
                                },
                                {
                                    "__typename": "Repository",
                                    "databaseId": 553624697,
                                    "name": "components-demo",
                                    "primaryLanguage": {"name": "Python"},
                                    "isPrivate": False,
                                    "defaultBranchRef": {"name": "main"},
                                    "owner": {
                                        "id": "U_kgDOBfIxWg",
                                        "login": "giovanni-guidini",
                                    },
                                },
                                {
                                    "__typename": "Organization",
                                    "name": "Codecov",
                                    "login": "codecov",
                                    "databaseId": 8226205,
                                },
                                {
                                    "__typename": "User",
                                    "login": "giovanni-guidini",
                                    "databaseId": 99758426,
                                },
                            ]
                        },
                        "extensions": {
                            "warnings": [
                                {
                                    "type": "DEPRECATION",
                                    "message": "The id MDEyOk9yZ2FuaXphdGlvbjgyMjYyMDU= is deprecated. Update your cache to use the next_global_id from the data payload.",
                                    "data": {
                                        "legacy_global_id": "MDEyOk9yZ2FuaXphdGlvbjgyMjYyMDU=",
                                        "next_global_id": "O_kgDOAH2FnQ",
                                    },
                                    "link": "https://docs.github.com",
                                }
                            ]
                        },
                    },
                )
            if "query GetOwnerFromNodeId" in content_string:
                return httpx.Response(
                    status_code=200,
                    json={
                        "data": {
                            "node": {
                                "__typename": "Organization",
                                "name": "Codecov",
                                "login": "codecov",
                                "databaseId": 8226205,
                            },
                        }
                    },
                )
            raise Exception("Unexpected request")

        # Actual test
        with respx.mock:
            mocked_route = respx.post("https://api.github.com/graphql").mock(
                side_effect=mock_route_side_effect
            )
            node_ids = [
                "R_kgDOG3OrZg",  # codecov/codecov-cli
                "R_kgDOJ643tA",  # codecov/worker
                "R_kgDOIP-keQ",  # giovanni-guidini/components-demo
                "MDEyOk9yZ2FuaXphdGlvbjgyMjYyMDU=",  # codecov
                "U_kgDOBfIxWg",  # giovanni-guidini
            ]
            request = ghapp_handler.get_repos_from_nodeids_generator(
                repo_node_ids=node_ids, expected_owner_username="giovanni-guidini"
            )
            repos = []
            async for repo in request:
                repos.append(repo)
            assert repos == [
                {
                    "branch": "main",
                    "language": "python",
                    "name": "codecov-cli",
                    "owner": {
                        "is_expected_owner": False,
                        "node_id": "MDEyOk9yZ2FuaXphdGlvbjgyMjYyMDU=",
                        "service_id": 8226205,
                        "username": "codecov",
                    },
                    "service_id": 460565350,
                    "private": False,
                },
                {
                    "branch": "main",
                    "language": "python",
                    "name": "worker",
                    "owner": {
                        "is_expected_owner": False,
                        "node_id": "MDEyOk9yZ2FuaXphdGlvbjgyMjYyMDU=",
                        "service_id": 8226205,
                        "username": "codecov",
                    },
                    "service_id": 665728948,
                    "private": False,
                },
                {
                    "branch": "main",
                    "language": "python",
                    "name": "components-demo",
                    "owner": {
                        "is_expected_owner": True,
                        "node_id": "U_kgDOBfIxWg",
                        "username": "giovanni-guidini",
                    },
                    "service_id": 553624697,
                    "private": False,
                },
            ]
            assert mocked_route.call_count == 2
        after = REGISTRY.get_sample_value(
            "git_provider_api_calls_github_total",
            labels={"endpoint": "get_repos_from_nodeids_generator_graphql"},
        )
        assert after - before == 1
        after_get_owner = REGISTRY.get_sample_value(
            "git_provider_api_calls_github_total",
            labels={"endpoint": "get_owner_from_nodeid_graphql"},
        )
        assert after_get_owner - before_get_owner == 1

    @pytest.mark.asyncio
    async def test_count_and_get_url_template(self, ghapp_handler):
        before = REGISTRY.get_sample_value(
            "git_provider_api_calls_github_total",
            labels={"endpoint": "make_http_call_retry"},
        )
        res = ghapp_handler.count_and_get_url_template(url_name="make_http_call_retry")
        assert res == ""
        after = REGISTRY.get_sample_value(
            "git_provider_api_calls_github_total",
            labels={"endpoint": "make_http_call_retry"},
        )
        assert after - before == 1

    @pytest.mark.asyncio
    async def test_count_and_get_url_template_unrecognized(self, ghapp_handler):
        with pytest.raises(KeyError):
            ghapp_handler.count_and_get_url_template(url_name="whoops")
