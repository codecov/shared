import json

import oauth2 as oauth
import pytest

from shared.torngit.bitbucket_server import BitbucketServer
from shared.torngit.exceptions import (
    TorngitClientGeneralError,
    TorngitObjectNotFoundError,
)


@pytest.fixture
def valid_handler():
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
    async def test_fetch_uses_proper_endpoint(
        self, valid_handler, mocker, mock_configuration
    ):
        response_dict = {"status": 201, "content-type": "application/json"}
        content = json.dumps({"id": "198", "version": "3"})
        mocked_fetch = mocker.patch.object(
            oauth.Client, "request", return_value=(response_dict, content)
        )
        mock_configuration._params["bitbucket_server"] = {
            "url": "https://bitbucketserver.codecov.dev",
            "api_url": "https://api.gitlab.dev",
        }

        res = await valid_handler.post_comment("pullid", "body")
        assert res == {"id": "198:3"}
        mocked_fetch.assert_called_with(
            "https://bitbucketserver.codecov.dev/rest/api/1.0/projects/THIAGOCODECOV/repos/example-python/pull-requests/pullid/comments",
            "POST",
            b'{"text": "body"}',
            headers={"Content-Type": "application/json"},
        )

    @pytest.mark.asyncio
    async def test_api_client_not_found(self, valid_handler, mocker):
        response_dict = {"status": 404, "content-type": "application/json"}
        content = json.dumps({})
        mocked_fetch = mocker.patch.object(
            oauth.Client, "request", return_value=(response_dict, content)
        )
        client = mocker.MagicMock(
            request=mocker.AsyncMock(return_value=mocker.MagicMock(status_code=404))
        )
        method = "GET"
        url = "random_url"
        with pytest.raises(TorngitClientGeneralError):
            await valid_handler.api(method, url)

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
    async def test_get_source_object_not_found(self, valid_handler, mocker):
        response_dict = {"status": 404, "content-type": "application/json"}
        content = json.dumps({})
        mocked_fetch = mocker.patch.object(
            oauth.Client, "request", return_value=(response_dict, content)
        )
        client = mocker.MagicMock(
            request=mocker.AsyncMock(return_value=mocker.MagicMock(status_code=404))
        )
        path = "some/path/"
        ref = "commitsha"
        with pytest.raises(TorngitObjectNotFoundError):
            await valid_handler.get_source(path, ref)
