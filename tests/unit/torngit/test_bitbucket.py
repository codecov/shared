import httpx
import respx
import pytest
from urllib.parse import urlparse, parse_qsl

from shared.torngit.bitbucket import Bitbucket

from shared.torngit.exceptions import (
    TorngitServerUnreachableError,
    TorngitServer5xxCodeError,
    TorngitClientError,
)


@pytest.fixture
def respx_vcr():
    with respx.mock as v:
        yield v


@pytest.fixture
def valid_handler():
    return Bitbucket(
        repo=dict(name="example-python"),
        owner=dict(
            username="ThiagoCodecov", service_id="6ef29b63-1288-4ceb-8dfc-af2c03f5cd49"
        ),
        oauth_consumer_token=dict(
            key="oauth_consumer_key_value", secret="oauth_consumer_token_secret_value"
        ),
        token=dict(secret="somesecret", key="somekey"),
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

    @pytest.mark.asyncio
    async def test_api_client_proper_params(self, valid_handler, mocker):
        client = mocker.MagicMock(
            request=mocker.AsyncMock(
                return_value=mocker.MagicMock(text="kowabunga", status_code=200)
            )
        )
        method = "GET"
        url = "/random_url"
        res = await valid_handler.api(client, "2", method, url)
        assert res == "kowabunga"
        assert client.request.call_count == 1
        args, kwargs = client.request.call_args
        assert len(args) == 2
        assert args[0] == "GET"
        built_url = args[1]
        parsed_url = urlparse(built_url)
        assert parsed_url.scheme == "https"
        assert parsed_url.netloc == "bitbucket.org"
        assert parsed_url.path == "/api/2.0/random_url"
        assert parsed_url.params == ""
        assert parsed_url.fragment == ""
        query = dict(parse_qsl(parsed_url.query, keep_blank_values=True))
        assert sorted(query.keys()) == [
            "oauth_consumer_key",
            "oauth_nonce",
            "oauth_signature",
            "oauth_signature_method",
            "oauth_timestamp",
            "oauth_token",
            "oauth_version",
        ]
        assert (
            query["oauth_consumer_key"] == "oauth_consumer_key_value"
        )  # defined on `valid_handler`
        assert query["oauth_signature_method"] == "HMAC-SHA1"
        assert query["oauth_token"] == "somekey"  # defined on `valid_handler`
        assert query["oauth_version"] == "1.0"  # our class uses

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

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "permission_name, expected_result",
        [("read", (True, False)), ("write", (True, True)), ("admin", (True, True))],
    )
    async def test_get_authenticated_private_200_status_some_permissions(
        self, mocker, respx_vcr, permission_name, expected_result
    ):
        respx.get(
            "https://bitbucket.org/api/2.0/repositories/ThiagoCodecov/example-python"
        ).respond(
            status_code=200, json={},
        )
        respx.get(
            "https://bitbucket.org/api/2.0/user/permissions/repositories"
        ).respond(
            status_code=200,
            json={
                "pagelen": 10,
                "values": [
                    {
                        "type": "repository_permission",
                        "user": {
                            "display_name": "Thiago Ramos",
                            "uuid": "{9a01f37b-b1b2-40c5-8c5e-1a39f4b5e645}",
                            "links": {},
                            "nickname": "thiago",
                            "type": "user",
                            "account_id": "5bce04c759d0e84f8c7555e9",
                        },
                        "repository": {
                            "links": {},
                            "type": "repository",
                            "name": "example-python",
                            "full_name": "ThiagoCodecov/example-python",
                            "uuid": "{a8c50527-2c3a-480e-afe1-7700e2b00074}",
                        },
                        "permission": permission_name,
                    }
                ],
                "page": 1,
            },
        )
        handler = Bitbucket(
            repo=dict(name="example-python", private=True),
            owner=dict(
                username="ThiagoCodecov",
                service_id="6ef29b63-1288-4ceb-8dfc-af2c03f5cd49",
            ),
            oauth_consumer_token=dict(
                key="oauth_consumer_key_value",
                secret="oauth_consumer_token_secret_value",
            ),
            token=dict(secret="somesecret", key="somekey"),
        )
        res = await handler.get_authenticated()
        assert res == expected_result

    @pytest.mark.asyncio
    async def test_get_authenticated_private_200_status_no_permission(
        self, mocker, respx_vcr
    ):
        respx.get(
            "https://bitbucket.org/api/2.0/repositories/ThiagoCodecov/example-python"
        ).respond(
            status_code=200, json={},
        )
        respx.get(
            "https://bitbucket.org/api/2.0/user/permissions/repositories"
        ).respond(
            status_code=200, json={"pagelen": 10, "values": [], "page": 1},
        )
        handler = Bitbucket(
            repo=dict(name="example-python", private=True),
            owner=dict(
                username="ThiagoCodecov",
                service_id="6ef29b63-1288-4ceb-8dfc-af2c03f5cd49",
            ),
            oauth_consumer_token=dict(
                key="oauth_consumer_key_value",
                secret="oauth_consumer_token_secret_value",
            ),
            token=dict(secret="somesecret", key="somekey"),
        )
        res = await handler.get_authenticated()
        assert res == (True, False)

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "permission_name, expected_result",
        [("read", (True, False)), ("write", (True, True)), ("admin", (True, True))],
    )
    async def test_get_authenticated_private_404_status(
        self, mocker, respx_vcr, permission_name, expected_result
    ):
        respx.get(
            "https://bitbucket.org/api/2.0/repositories/ThiagoCodecov/example-python"
        ).respond(
            status_code=404, json={},
        )
        handler = Bitbucket(
            repo=dict(name="example-python", private=True),
            owner=dict(
                username="ThiagoCodecov",
                service_id="6ef29b63-1288-4ceb-8dfc-af2c03f5cd49",
            ),
            oauth_consumer_token=dict(
                key="oauth_consumer_key_value",
                secret="oauth_consumer_token_secret_value",
            ),
            token=dict(secret="secret", key="key"),
        )
        with pytest.raises(TorngitClientError):
            await handler.get_authenticated()
