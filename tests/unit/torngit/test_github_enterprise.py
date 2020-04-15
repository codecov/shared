from asyncio import Future
import pytest

from shared.torngit.github_enterprise import GithubEnterprise


class TestGithubEnterprise(object):
    def test_urls_no_api_url_set(self, mock_configuration):
        mock_configuration._params["github_enterprise"] = {
            "url": "https://github-enterprise.codecov.dev"
        }
        gl = GithubEnterprise()
        assert gl.service_url == "https://github-enterprise.codecov.dev"
        assert gl.api_url == "https://github-enterprise.codecov.dev/api/v3"

    def test_urls_with_api_url_set(self, mock_configuration):
        mock_configuration._params["github_enterprise"] = {
            "url": "https://github-enterprise.codecov.dev",
            "api_url": "https://api.github.dev",
        }
        gl = GithubEnterprise()
        assert gl.service_url == "https://github-enterprise.codecov.dev"
        assert gl.api_url == "https://api.github.dev"

    @pytest.mark.asyncio
    async def test_fetch_uses_proper_endpoint(self, mocker, mock_configuration):
        mocked_fetch = mocker.patch.object(
            GithubEnterprise, "fetch", return_value=Future()
        )
        mocked_fetch.return_value.set_result(
            mocker.MagicMock(headers={"Content-Type": "application/json"}, body="{}")
        )
        mock_configuration._params["github_enterprise"] = {
            "url": "https://github-enterprise.codecov.dev",
            "api_url": "https://api.github.dev",
        }
        gl = GithubEnterprise(
            repo=dict(service_id="187725", name="codecov-test"),
            owner=dict(username="stevepeak", service_id="109479"),
            token=dict(key="fake_token"),
        )
        res = await gl.post_comment("pullid", "body")
        assert res == {}
        mocked_fetch.assert_called_with(
            "https://api.github.dev/repos/stevepeak/codecov-test/issues/pullid/comments",
            body='{"body": "body"}',
            ca_certs=None,
            connect_timeout=10,
            headers={
                "Accept": "application/json",
                "Authorization": "token fake_token",
                "User-Agent": "Default",
            },
            follow_redirects=False,
            method="POST",
            request_timeout=30,
            validate_cert=None,
        )
