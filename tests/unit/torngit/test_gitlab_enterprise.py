import pytest

from shared.torngit.gitlab_enterprise import GitlabEnterprise


class TestGitlabEnterprise(object):
    def test_urls_no_api_url_set(self, mock_configuration):
        mock_configuration._params["gitlab_enterprise"] = {
            "url": "https://gitlab-enterprise.codecov.dev"
        }
        gl = GitlabEnterprise()
        assert gl.service_url == "https://gitlab-enterprise.codecov.dev"
        assert gl.api_url == "https://gitlab-enterprise.codecov.dev/api/v4"
        assert (
            GitlabEnterprise.get_service_url()
            == "https://gitlab-enterprise.codecov.dev"
        )
        assert (
            GitlabEnterprise.get_api_url()
            == "https://gitlab-enterprise.codecov.dev/api/v4"
        )

    def test_urls_with_api_url_set(self, mock_configuration):
        mock_configuration._params["gitlab_enterprise"] = {
            "url": "https://gitlab-enterprise.codecov.dev",
            "api_url": "https://api.gitlab.dev",
        }
        gl = GitlabEnterprise()
        assert gl.service_url == "https://gitlab-enterprise.codecov.dev"
        assert gl.api_url == "https://api.gitlab.dev"

    @pytest.mark.asyncio
    async def test_fetch_uses_proper_endpoint(self, mocker, mock_configuration):
        mocked_fetch = mocker.patch.object(
            GitlabEnterprise, "api", return_value={}
        )
        mock_configuration._params["gitlab_enterprise"] = {
            "url": "https://gitlab-enterprise.codecov.dev",
            "api_url": "https://api.gitlab.dev",
        }
        gl = GitlabEnterprise(
            repo=dict(service_id="187725", name="codecov-test"),
            owner=dict(username="stevepeak", service_id="109479"),
            token=dict(key="fake_token"),
        )
        res = await gl.post_comment("pullid", "body")
        assert res == {}
        mocked_fetch.assert_called_with(
            "post",
            "/projects/187725/merge_requests/pullid/notes",
            body={"body": "body"},
            token={'key': 'fake_token'},
        )
