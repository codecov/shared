import json
import pytest

import oauth2 as oauth

from shared.torngit.bitbucket_server import BitbucketServer


class TestBitbucketServer(object):
    def test_service_url(self, mock_configuration):
        mock_configuration._params["bitbucket_server"] = {
            "url": "https://bitbucketserver.codecov.dev"
        }
        gl = BitbucketServer()
        assert gl.service_url == "https://bitbucketserver.codecov.dev"
        assert (
            BitbucketServer.get_service_url() == "https://bitbucketserver.codecov.dev"
        )

    @pytest.mark.asyncio
    async def test_fetch_uses_proper_endpoint(self, mocker, mock_configuration):
        response_dict = {"status": 201, "content-type": "application/json"}
        content = json.dumps({"id": "198", "version": "3"})
        mocked_fetch = mocker.patch.object(
            oauth.Client, "request", return_value=(response_dict, content)
        )
        mock_configuration._params["bitbucket_server"] = {
            "url": "https://bitbucketserver.codecov.dev",
            "api_url": "https://api.gitlab.dev",
        }
        gl = BitbucketServer(
            repo=dict(name="example-python"),
            owner=dict(
                username="ThiagoCodecov",
                service_id="6ef29b63-1288-4ceb-8dfc-af2c03f5cd49",
            ),
            oauth_consumer_token=dict(
                key="test51hdmhalc053rb", secret="testrgj6ezg5b4zc5z8t2rspg90rw6dp"
            ),
            token=dict(
                secret="test3spp3gm9db4f43y0zfm2jvvkpnd6", key="testm0141jl7b6ux9l"
            ),
        )
        res = await gl.post_comment("pullid", "body")
        assert res == {"id" : "198:3"}
        mocked_fetch.assert_called_with(
            "https://bitbucketserver.codecov.dev/rest/api/1.0/projects/THIAGOCODECOV/repos/example-python/pull-requests/pullid/comments",
            "POST",
            b'{"text": "body"}',
            headers={"Content-Type": "application/json"},
        )
