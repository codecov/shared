import asyncio
from unittest.mock import MagicMock
from urllib.parse import parse_qs
from urllib.request import Request

import httpx
import pytest
import respx

from shared.torngit.base import TokenType
from shared.torngit.exceptions import (
    TorngitCantRefreshTokenError,
    TorngitClientGeneralError,
    TorngitRefreshTokenFailedError,
    TorngitServer5xxCodeError,
)
from shared.torngit.gitlab import Gitlab


@pytest.fixture
def valid_handler():
    return Gitlab(
        repo=dict(service_id="187725", name="codecov-test"),
        owner=dict(username="ThiagoCodecov", service_id="109479"),
        oauth_consumer_token=dict(
            key="client_id",
            secret="client_secret",
        ),
        token=dict(key="access_token", refresh_token="refresh_token"),
    )


class TestUnitGitlab(object):
    def test_redirect_uri_default(self):
        gl = Gitlab()
        assert gl.redirect_uri == "https://codecov.io/login/gitlab"

    def test_redirect_uri_custom_redirect(self, mock_configuration):
        gl = Gitlab()
        mock_configuration._params.update(
            {"gitlab": {"redirect_uri": "https://custom_redirect.com"}}
        )
        assert gl.redirect_uri == "https://custom_redirect.com"

    def test_redirect_uri_custom_base(self, mock_configuration):
        gl = Gitlab()

        mock_configuration._params.update(
            {"setup": {"codecov_url": "http://localhost"}}
        )
        assert gl.redirect_uri == "http://localhost/login/gitlab"

    @pytest.mark.asyncio
    async def test_get_commit_statuses(self, mocker, valid_handler):
        mocked_fetch = mocker.patch.object(
            Gitlab,
            "api",
            return_value=[
                {
                    "status": "success",
                    "description": "Successful status",
                    "target_url": "url",
                    "name": "name",
                    "finished_at": None,
                    "created_at": None,
                },
                {
                    "status": None,
                    "description": "None status",
                    "target_url": "url",
                    "name": "name",
                    "created_at": "not none",
                },
            ],
        )
        res = await valid_handler.get_commit_statuses(
            "c739768fcac68144a3a6d82305b9c4106934d31a"
        )
        assert res == "failure"

    @pytest.mark.asyncio
    async def test_get_commit_statuses_success(self, mocker, valid_handler):
        mocked_fetch = mocker.patch.object(
            Gitlab,
            "api",
            return_value=[
                {
                    "status": "success",
                    "description": "Successful status",
                    "target_url": "url",
                    "name": "name",
                    "created_at": "not none",
                },
                {
                    "status": "success",
                    "description": "Another successful status",
                    "target_url": "url",
                    "name": "name",
                    "created_at": "not none",
                },
                {
                    "status": "skipped",
                    "description": "This was skipped so still counts as success",
                    "target_url": "url",
                    "name": "name",
                    "created_at": "not none",
                },
            ],
        )
        res = await valid_handler.get_commit_statuses(
            "c739768fcac68144a3a6d82305b9c4106934d31a"
        )
        assert res == "success"

    @pytest.mark.asyncio
    async def test_get_commit_statuses_pending(self, mocker, valid_handler):
        mocked_fetch = mocker.patch.object(
            Gitlab,
            "api",
            return_value=[
                {
                    "status": "created",
                    "description": "Created means still pending",
                    "target_url": "url",
                    "name": "name",
                    "created_at": "not none",
                },
                {
                    "status": "manual",
                    "description": "This requires a manual run so we'll consider it pending until then",
                    "target_url": "url",
                    "name": "name",
                    "created_at": "not none",
                },
                {
                    "status": "waiting_for_resource",
                    "description": "Waiting for a resource",
                    "target_url": "url",
                    "name": "name",
                    "created_at": "not none",
                },
            ],
        )
        res = await valid_handler.get_commit_statuses(
            "c739768fcac68144a3a6d82305b9c4106934d31a"
        )
        assert res == "pending"

    @pytest.mark.asyncio
    async def test_find_pull_request_by_commit_endpoint_doesnt_find_old_does(
        self, mocker, valid_handler
    ):
        commit_sha = "c739768fcac68144a3a6d82305b9c4106934d31a"
        first_result = []
        second_result = [{"sha": "aaaa", "iid": 123}, {"sha": commit_sha, "iid": 986}]
        results = [first_result, second_result]
        mocker.patch.object(Gitlab, "api", side_effect=results)
        res = await valid_handler.find_pull_request(commit_sha)
        assert res == 986

    def test_get_token_by_type_if_none(self):
        instance = Gitlab(
            token="token",
            token_type_mapping={
                TokenType.read: "read",
                TokenType.admin: "admin",
                TokenType.comment: None,
                TokenType.status: "status",
            },
        )
        assert instance.get_token_by_type_if_none(None, TokenType.read) == "read"
        assert instance.get_token_by_type_if_none(None, TokenType.admin) == "admin"
        assert instance.get_token_by_type_if_none(None, TokenType.comment) == "token"
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
    async def test_gitlab_url_spaces_percent_encoded(self, mocker, valid_handler):
        with respx.mock:
            mocked_route = respx.get("https://gitlab.com/api/v4/endpoint%20name").mock(
                return_value=httpx.Response(status_code=200, json="{}")
            )
            await valid_handler.api("get", "/endpoint name")

        assert mocked_route.call_count == 1

    @pytest.mark.asyncio
    async def test_gitlab_get_source_path_with_spaces(self, mocker, valid_handler):
        with respx.mock:
            mocked_route = respx.get(
                "https://gitlab.com/api/v4/projects/187725/repository/files/tests%20with%20space.py?ref=master"
            ).mock(
                return_value=httpx.Response(
                    status_code=200,
                    content='{"commitid": null, "content": "code goes here"}',
                )
            )
            await valid_handler.get_source("tests with space.py", "master")
        assert mocked_route.call_count == 1

    @pytest.mark.asyncio
    async def test_gitlab_refresh_fail_terminates_unavailable(
        self, mocker, valid_handler
    ):
        with pytest.raises(TorngitRefreshTokenFailedError):
            with respx.mock:
                mocked_refresh = respx.post("https://gitlab.com/oauth/token").mock(
                    return_value=httpx.Response(
                        status_code=502, content="Service unavailable try again later"
                    )
                )
                await valid_handler.refresh_token(valid_handler.get_client())
        mocked_refresh.call_count == 1

    @pytest.mark.asyncio
    async def test_gitlab_refresh_fail_terminates_bad_request(
        self, mocker, valid_handler
    ):
        with pytest.raises(TorngitRefreshTokenFailedError):
            with respx.mock:
                mocked_refresh = respx.post("https://gitlab.com/oauth/token").mock(
                    return_value=httpx.Response(
                        status_code=403, content='{"error": "unauthorized"}'
                    )
                )
                await valid_handler.refresh_token(valid_handler.get_client())
        mocked_refresh.call_count == 1

    @pytest.mark.asyncio
    async def test_gitlab_refresh_fail_terminates_bad_request(
        self, mocker, valid_handler
    ):
        valid_handler._token = {"access_token": "old_token_without_refresh"}
        with pytest.raises(TorngitCantRefreshTokenError):
            with respx.mock:
                mocked_refresh = respx.post("https://gitlab.com/oauth/token").mock(
                    return_value=httpx.Response(
                        status_code=403, content='{"error": "unauthorized"}'
                    )
                )
                await valid_handler.refresh_token(valid_handler.get_client())
        mocked_refresh.call_count == 1

    @pytest.mark.asyncio
    async def test_gitlab_double_refresh(self, mocker, valid_handler):
        def side_effect(request, *args, **kwargs):
            parsed_content = parse_qs(request.content)
            refresh_token = parsed_content[b"refresh_token"][0]
            if refresh_token == b"refresh_token":
                return httpx.Response(
                    status_code=200,
                    content='{"access_token": "new_access_token","token_type": "bearer","refresh_token": "new_refresh_token"}',
                )
            elif refresh_token == b"new_refresh_token":
                return httpx.Response(
                    status_code=200,
                    content='{"access_token": "newer_access_token","token_type": "bearer","refresh_token": "newer_refresh_token"}',
                )
            pytest.fail(f"Wrong token received")

        assert valid_handler._oauth == dict(key="client_id", secret="client_secret")

        with respx.mock:
            mocked_refresh = respx.post("https://gitlab.com/oauth/token").mock(
                side_effect=side_effect
            )
            await valid_handler.refresh_token(valid_handler.get_client())
            assert mocked_refresh.call_count == 1
            assert valid_handler._token == dict(
                key="new_access_token", refresh_token="new_refresh_token"
            )

            await valid_handler.refresh_token(valid_handler.get_client())
            assert mocked_refresh.call_count == 2
            assert valid_handler._token == dict(
                key="newer_access_token", refresh_token="newer_refresh_token"
            )

        # Make sure that changing the token doesn't change the _oauth
        assert valid_handler._oauth == dict(key="client_id", secret="client_secret")

    @pytest.mark.asyncio
    async def test_gitlab_refresh_after_failed_request(self, mocker, valid_handler):
        def side_effect(request, *args, **kwargs):
            token = request.headers["Authorization"]
            if token == "Bearer access_token":
                return httpx.Response(
                    status_code=401,
                    content='{"error":"invalid_token","error_description":"Token is expired. You can either do re-authorization or token refresh."}',
                )
            elif token == "Bearer new_access_token":
                return httpx.Response(
                    status_code=200,
                    content='{"commitid": null, "content": "code goes here"}',
                )
            pytest.fail(f"Wrong token received ({token})")

        f = asyncio.Future()
        f.set_result(True)
        mock_refresh_callback: MagicMock = mocker.patch.object(
            valid_handler, "_on_token_refresh", create=True, return_value=f
        )
        with respx.mock:
            mocked_route = respx.get(
                "https://gitlab.com/api/v4/projects/187725/repository/files/tests%20with%20space.py?ref=master"
            ).mock(side_effect=side_effect)
            mocked_refresh = respx.post("https://gitlab.com/oauth/token").mock(
                return_value=httpx.Response(
                    status_code=200,
                    content='{"access_token": "new_access_token","token_type": "bearer","refresh_token": "new_refresh_token"}',
                )
            )
            await valid_handler.get_source("tests with space.py", "master")
        assert mocked_route.call_count == 2
        assert mocked_refresh.call_count == 1
        assert valid_handler._token["key"] == "new_access_token"
        assert valid_handler._token["refresh_token"] == "new_refresh_token"
        assert mock_refresh_callback.call_count == 1
        assert mock_refresh_callback.called_with(
            {
                "access_token": "new_access_token",
                "refresh_token": "new_refresh_token",
            }
        )
