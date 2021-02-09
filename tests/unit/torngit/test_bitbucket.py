import httpx
import respx
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
    async def test_api_client_error_connect_error(self, valid_handler, mocker):
        client = mocker.MagicMock(
            request=mocker.AsyncMock(
                side_effect=httpx.ConnectError("message", request="request")
            )
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

    def test_generate_request_token(self, valid_handler):
        with respx.mock:
            my_route = respx.get(
                "https://bitbucket.org/api/1.0/oauth/request_token"
            ).mock(
                return_value=httpx.Response(
                    status_code=200,
                    content="oauth_token_secret=test7f35jt40fnbz5xanwn9tlsi5ci10&oauth_token=testh3xen5q215b9ex&oauth_callback_confirmed=true",
                )
            )
            v = valid_handler.generate_request_token("127.0.0.1/bb")
            assert v == {
                "oauth_token": "testh3xen5q215b9ex",
                "oauth_token_secret": "test7f35jt40fnbz5xanwn9tlsi5ci10",
            }
            assert my_route.call_count == 1

    def test_generate_access_token(self, valid_handler):
        with respx.mock:
            my_route = respx.get(
                "https://bitbucket.org/api/1.0/oauth/access_token"
            ).mock(
                return_value=httpx.Response(
                    status_code=200,
                    content="oauth_token_secret=test3j3wxslwkw2j27ncbntpcwq50kzh&oauth_token=testss3hxhcfqf1h6g",
                )
            )
            cookie_key, cookie_secret, oauth_verifier = (
                "rz5RKUeSbag6eeGrYj",
                "WG8RYGfhMggdj6aKVhHq4qtSUJq4paDX",
                "7403692316",
            )
            v = valid_handler.generate_access_token(
                cookie_key, cookie_secret, oauth_verifier
            )
            assert v == {
                "key": "testss3hxhcfqf1h6g",
                "secret": "test3j3wxslwkw2j27ncbntpcwq50kzh",
            }
            assert my_route.call_count == 1
