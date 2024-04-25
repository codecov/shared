from urllib.parse import urlparse

import pytest
from prometheus_client import REGISTRY

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
        before = REGISTRY.get_sample_value(
            "git_provider_api_calls_github_enterprise_total",
            labels={"endpoint": "post_comment"},
        )
        client = mocker.MagicMock(
            __aenter__=mocker.AsyncMock(
                return_value=mocker.MagicMock(
                    request=mocker.AsyncMock(
                        return_value=mocker.MagicMock(
                            headers={"Content-Type": "application/json"},
                            status_code=201,
                            json=mocker.MagicMock(return_value={}),
                        )
                    )
                )
            )
        )
        mocker.patch.object(GithubEnterprise, "get_client", return_value=client)
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
            follow_redirects=False,
        )
        after = REGISTRY.get_sample_value(
            "git_provider_api_calls_github_enterprise_total",
            labels={"endpoint": "post_comment"},
        )
        assert after - before == 1

    @pytest.mark.asyncio
    async def test_api_client_change_api_host(self, mocker, mock_configuration):
        mock_host = "legit-ghe"
        mock_configuration._params["github_enterprise"] = {
            "api_url": "https://" + mock_host,
            "api_host_override": "api.ghe.com",
        }
        client = mocker.MagicMock(
            request=mocker.AsyncMock(
                return_value=mocker.MagicMock(text="kowabunga", status_code=200)
            )
        )
        mocker.patch.object(GithubEnterprise, "get_client", return_value=client)
        gl = GithubEnterprise(
            repo=dict(service_id="187725", name="codecov-test"),
            owner=dict(username="stevepeak", service_id="109479"),
            token=dict(key="fake_token"),
        )
        method = "GET"
        url = "/random_url"
        query_params = {"qparam1": "a param", "qparam2": "another param"}
        res = await gl.api(client, method, url, **query_params)
        assert res == "kowabunga"
        assert client.request.call_count == 1
        args, kwargs = client.request.call_args
        assert kwargs.get("headers") is not None
        assert kwargs.get("headers").get("Host") == "api.ghe.com"
        assert len(args) == 2
        built_url = args[1]
        parsed_url = urlparse(built_url)
        assert parsed_url.scheme == "https"
        assert parsed_url.netloc == mock_host
        assert parsed_url.path == url
        assert parsed_url.params == ""
        assert parsed_url.fragment == ""

    @pytest.mark.asyncio
    async def test_make_http_call_change_host(self, mocker, mock_configuration):
        mock_host = "legit-ghe"
        mock_configuration._params["github_enterprise"] = {
            "url": "https://" + mock_host,
            "host_override": "ghe.com",
        }
        client = mocker.MagicMock(
            request=mocker.AsyncMock(
                return_value=mocker.MagicMock(text="kowabunga", status_code=200)
            )
        )
        mocker.patch.object(GithubEnterprise, "get_client", return_value=client)
        gl = GithubEnterprise(
            repo=dict(service_id="187725", name="codecov-test"),
            owner=dict(username="stevepeak", service_id="109479"),
            token=dict(key="fake_token"),
        )
        method = "GET"
        url = f"https://{mock_host}/random_url"
        query_params = {"qparam1": "a param", "qparam2": "another param"}
        await gl.make_http_call(client, method, url, **query_params)
        assert client.request.call_count == 1
        args, kwargs = client.request.call_args
        print(args)
        print(kwargs)
        assert kwargs.get("headers") is not None
        assert kwargs.get("headers").get("Host") == "ghe.com"
        assert len(args) == 2
        built_url = args[1]
        parsed_url = urlparse(built_url)
        print(parsed_url)
        assert parsed_url.scheme == "https"
        assert parsed_url.netloc == mock_host
        assert parsed_url.path == "/random_url"
        assert parsed_url.params == ""
        assert parsed_url.fragment == ""
