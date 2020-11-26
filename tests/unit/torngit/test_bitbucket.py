import httpx

import pytest

from shared.torngit.bitbucket import Bitbucket

from shared.torngit.exceptions import (
    TorngitServerUnreachableError,
    TorngitServer5xxCodeError,
    TorngitClientError,
)


@pytest.fixture
def valid_handler():
    return Bitbucket(
        repo=dict(name="example-python"),
        owner=dict(
            username="ThiagoCodecov", service_id="6ef29b63-1288-4ceb-8dfc-af2c03f5cd49"
        ),
        oauth_consumer_token=dict(
            key="test51hdmhalc053rb", secret="testrgj6ezg5b4zc5z8t2rspg90rw6dp"
        ),
        token=dict(secret="test3spp3gm9db4f43y0zfm2jvvkpnd6", key="testm0141jl7b6ux9l"),
    )


class TestUnitBitbucket(object):
    @pytest.mark.asyncio
    async def test_api_client_error_unreachable(self, valid_handler, mocker):
        client = mocker.MagicMock(
            request=mocker.AsyncMock(return_value=mocker.MagicMock(status_code=599))
        )
        method = "GET"
        url = "random_url"
        with pytest.raises(TorngitServerUnreachableError):
            await valid_handler.api(client, "2", method, url)

    @pytest.mark.asyncio
    async def test_api_client_error_server_error(self, valid_handler, mocker):
        client = mocker.MagicMock(
            request=mocker.AsyncMock(return_value=mocker.MagicMock(status_code=503))
        )
        method = "GET"
        url = "random_url"
        with pytest.raises(TorngitServer5xxCodeError):
            await valid_handler.api(client, "2", method, url)

    @pytest.mark.asyncio
    async def test_api_client_error_client_error(self, valid_handler, mocker):
        client = mocker.MagicMock(
            request=mocker.AsyncMock(return_value=mocker.MagicMock(status_code=404))
        )
        method = "GET"
        url = "random_url"
        with pytest.raises(TorngitClientError):
            await valid_handler.api(client, "2", method, url)
