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
        assert (
            GithubEnterprise.get_service_url()
            == "https://github-enterprise.codecov.dev"
        )
        assert (
            GithubEnterprise.get_api_url()
            == "https://github-enterprise.codecov.dev/api/v3"
        )

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
        client = mocker.MagicMock(
            __aenter__=mocker.AsyncMock(
                return_value=mocker.MagicMock(
                    request=mocker.AsyncMock(
                        return_value=mocker.MagicMock(
                            headers={"Content-Type": "application/json"},
                            status_code=201,
                            json=mocker.MagicMock(return_value={}),
                        )
                    ),
                ),
            ),
        )
        mocked_fetch = mocker.patch.object(
            GithubEnterprise, "get_client", return_value=client
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
        client.__aenter__.return_value.request.assert_called_with(
            "POST",
            "https://api.github.dev/repos/stevepeak/codecov-test/issues/pullid/comments",
            json={"body": "body"},
            headers={
                "Accept": "application/json",
                "Authorization": "token fake_token",
                "User-Agent": "Default",
            },
            allow_redirects=False,
        )
