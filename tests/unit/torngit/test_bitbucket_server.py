import pytest

from shared.torngit.bitbucket_server import BitbucketServer
from shared.torngit.exceptions import (
    TorngitClientGeneralError,
    TorngitObjectNotFoundError,
)

MOCK_BASE = "https://bitbucketserver.codecov.dev"


@pytest.fixture
def valid_handler(mock_configuration):
    mock_configuration._params["bitbucket_server"] = {"url": MOCK_BASE}
    return BitbucketServer(
        repo=dict(name="example-python"),
        owner=dict(
            username="ThiagoCodecov", service_id="6ef29b63-aaaa-aaaa-aaaa-aaaa03f5cd49"
        ),
        oauth_consumer_token=dict(
            key="arubajamaicaohiwan", secret="natakeyoubermudabahamacomeonpret"
        ),
        token=dict(secret="KeyLargoMontegobabywhydontwego", key="waydowntokokomo"),
    )


class TestBitbucketServer(object):
    def test_service_url(self, mock_configuration):
        mock_configuration._params["bitbucket_server"] = {
            "url": "https://bitbucketserver.codecov.dev"
        }
        bbs = BitbucketServer()
        assert bbs.service_url == "https://bitbucketserver.codecov.dev"
        assert (
            BitbucketServer.get_service_url() == "https://bitbucketserver.codecov.dev"
        )

    @pytest.mark.asyncio
    @pytest.mark.respx(base_url=MOCK_BASE)
    async def test_fetch_uses_proper_endpoint(self, valid_handler, respx_mock):
        respx_mock.post(
            "/rest/api/1.0/projects/THIAGOCODECOV/repos/example-python/pull-requests/pullid/comments"
        ).respond(status_code=201, json={"id": 198, "version": 3})

        res = await valid_handler.post_comment("pullid", "body")
        assert res == {"id": "198:3"}

    @pytest.mark.asyncio
    async def test_api_client_not_found(self, valid_handler, respx_mock):
        respx_mock.get("/rest/api/1.0/random_url").respond(status_code=404, json={})

        with pytest.raises(TorngitClientGeneralError):
            await valid_handler.api("GET", "/random_url")

    @pytest.mark.asyncio
    async def test_get_repo_languages(self):
        expected_result = ["javascript"]
        handler = BitbucketServer(
            repo=dict(name="example-python", private=True),
        )
        res = await handler.get_repo_languages(None, "JavaScript")
        assert res == expected_result

    @pytest.mark.asyncio
    async def test_get_repo_no_languages(self):
        expected_result = []
        handler = BitbucketServer(
            repo=dict(name="example-python", private=True),
        )
        res = await handler.get_repo_languages(None, None)
        assert res == expected_result

    @pytest.mark.asyncio
    @pytest.mark.respx(base_url=MOCK_BASE)
    async def test_get_source_object_not_found(self, valid_handler, respx_mock):
        respx_mock.get(
            "/rest/api/1.0/projects/THIAGOCODECOV/repos/example-python/browse/some/path/"
        ).respond(status_code=404, json={})

        with pytest.raises(TorngitObjectNotFoundError):
            await valid_handler.get_source("some/path/", "commitsha")
