import httpx
import pytest
import respx

from shared.torngit.github import Github
from shared.torngit.base import TokenType

from shared.torngit.exceptions import (
    TorngitServerUnreachableError,
    TorngitServer5xxCodeError,
    TorngitClientError,
)


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
