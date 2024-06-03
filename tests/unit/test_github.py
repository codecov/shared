import pytest
from mock import MagicMock
from prometheus_client import REGISTRY
from redis import RedisError

from shared.github import (
    InvalidInstallationError,
    get_github_integration_token,
    is_installation_rate_limited,
    mark_installation_as_rate_limited,
)

# DONT WORRY, this is generated for the purposes of validation, and is not the real
# one on which the code ran
fake_private_key = """-----BEGIN RSA PRIVATE KEY-----
MIICXAIBAAKBgQDCFqq2ygFh9UQU/6PoDJ6L9e4ovLPCHtlBt7vzDwyfwr3XGxln
0VbfycVLc6unJDVEGZ/PsFEuS9j1QmBTTEgvCLR6RGpfzmVuMO8wGVEO52pH73h9
rviojaheX/u3ZqaA0di9RKy8e3L+T0ka3QYgDx5wiOIUu1wGXCs6PhrtEwICBAEC
gYBu9jsi0eVROozSz5dmcZxUAzv7USiUcYrxX007SUpm0zzUY+kPpWLeWWEPaddF
VONCp//0XU8hNhoh0gedw7ZgUTG6jYVOdGlaV95LhgY6yXaQGoKSQNNTY+ZZVT61
zvHOlPynt3GZcaRJOlgf+3hBF5MCRoWKf+lDA5KiWkqOYQJBAMQp0HNVeTqz+E0O
6E0neqQDQb95thFmmCI7Kgg4PvkS5mz7iAbZa5pab3VuyfmvnVvYLWejOwuYSp0U
9N8QvUsCQQD9StWHaVNM4Lf5zJnB1+lJPTXQsmsuzWvF3HmBkMHYWdy84N/TdCZX
Cxve1LR37lM/Vijer0K77wAx2RAN/ppZAkB8+GwSh5+mxZKydyPaPN29p6nC6aLx
3DV2dpzmhD0ZDwmuk8GN+qc0YRNOzzJ/2UbHH9L/lvGqui8I6WLOi8nDAkEA9CYq
ewfdZ9LcytGz7QwPEeWVhvpm0HQV9moetFWVolYecqBP4QzNyokVnpeUOqhIQAwe
Z0FJEQ9VWsG+Df0noQJBALFjUUZEtv4x31gMlV24oiSWHxIRX4fEND/6LpjleDZ5
C/tY+lZIEO1Gg/FxSMB+hwwhwfSuE3WohZfEcSy+R48=
-----END RSA PRIVATE KEY-----"""


class TestGithubSpecificLogic(object):
    def test_get_github_integration_token_enterprise(self, mocker, mock_configuration):
        before = REGISTRY.get_sample_value(
            "git_provider_api_calls_github_total",
            labels={"endpoint": "get_github_integration_token"},
        )
        e_before = REGISTRY.get_sample_value(
            "git_provider_api_calls_github_enterprise_total",
            labels={"endpoint": "get_github_integration_token"},
        )
        service = "github_enterprise"
        mock_configuration._params[service] = {"url": "http://legit-github"}
        integration_id = 1
        mocked_post = mocker.patch("shared.github.requests.post")
        mocked_post.return_value.json.return_value = {"token": "arriba"}
        mocker.patch("shared.github.get_pem", return_value=fake_private_key)
        assert get_github_integration_token(service, integration_id) == "arriba"
        mocked_post.assert_called_with(
            "http://legit-github/api/v3/app/installations/1/access_tokens",
            headers={
                "Accept": "application/vnd.github.machine-man-preview+json",
                "Authorization": mocker.ANY,
                "User-Agent": "Codecov",
            },
        )
        after = REGISTRY.get_sample_value(
            "git_provider_api_calls_github_total",
            labels={"endpoint": "get_github_integration_token"},
        )
        e_after = REGISTRY.get_sample_value(
            "git_provider_api_calls_github_enterprise_total",
            labels={"endpoint": "get_github_integration_token"},
        )
        assert after - before == 0
        assert e_after - e_before == 1

    def test_get_github_integration_token_enterprise_host_override(
        self, mocker, mock_configuration
    ):
        before = REGISTRY.get_sample_value(
            "git_provider_api_calls_github_total",
            labels={"endpoint": "get_github_integration_token"},
        )
        e_before = REGISTRY.get_sample_value(
            "git_provider_api_calls_github_enterprise_total",
            labels={"endpoint": "get_github_integration_token"},
        )
        service = "github_enterprise"
        mock_configuration._params[service] = {
            "url": "https://legit-github",
            "api_host_override": "some-other-github.com",
        }
        integration_id = 1
        mocked_post = mocker.patch("shared.github.requests.post")
        mocked_post.return_value.json.return_value = {"token": "arriba"}
        mocker.patch("shared.github.get_pem", return_value=fake_private_key)
        assert get_github_integration_token(service, integration_id) == "arriba"
        mocked_post.assert_called_with(
            "https://legit-github/api/v3/app/installations/1/access_tokens",
            headers={
                "Accept": "application/vnd.github.machine-man-preview+json",
                "Authorization": mocker.ANY,
                "User-Agent": "Codecov",
                "Host": "some-other-github.com",
            },
        )
        after = REGISTRY.get_sample_value(
            "git_provider_api_calls_github_total",
            labels={"endpoint": "get_github_integration_token"},
        )
        e_after = REGISTRY.get_sample_value(
            "git_provider_api_calls_github_enterprise_total",
            labels={"endpoint": "get_github_integration_token"},
        )
        assert after - before == 0
        assert e_after - e_before == 1

    def test_get_github_integration_token_production(self, mocker, mock_configuration):
        before = REGISTRY.get_sample_value(
            "git_provider_api_calls_github_total",
            labels={"endpoint": "get_github_integration_token"},
        )
        e_before = REGISTRY.get_sample_value(
            "git_provider_api_calls_github_enterprise_total",
            labels={"endpoint": "get_github_integration_token"},
        )
        service = "github"
        mock_configuration._params["github_enterprise"] = {"url": "http://legit-github"}
        integration_id = 1
        mocked_post = mocker.patch("shared.github.requests.post")
        mocked_post.return_value.json.return_value = {"token": "arriba"}
        mocker.patch("shared.github.get_pem", return_value=fake_private_key)
        assert get_github_integration_token(service, integration_id) == "arriba"
        mocked_post.assert_called_with(
            "https://api.github.com/app/installations/1/access_tokens",
            headers={
                "Accept": "application/vnd.github.machine-man-preview+json",
                "Authorization": mocker.ANY,
                "User-Agent": "Codecov",
            },
        )
        after = REGISTRY.get_sample_value(
            "git_provider_api_calls_github_total",
            labels={"endpoint": "get_github_integration_token"},
        )
        e_after = REGISTRY.get_sample_value(
            "git_provider_api_calls_github_enterprise_total",
            labels={"endpoint": "get_github_integration_token"},
        )
        assert after - before == 1
        assert e_after - e_before == 0

    def test_get_github_integration_token_production_host_override(
        self, mocker, mock_configuration
    ):
        before = REGISTRY.get_sample_value(
            "git_provider_api_calls_github_total",
            labels={"endpoint": "get_github_integration_token"},
        )
        e_before = REGISTRY.get_sample_value(
            "git_provider_api_calls_github_enterprise_total",
            labels={"endpoint": "get_github_integration_token"},
        )
        service = "github"
        api_url = "https://legit-github"
        mock_configuration._params["github"] = {
            "api_url": api_url,
            "api_host_override": "api.github.com",
        }
        integration_id = 1
        mocked_post = mocker.patch("shared.github.requests.post")
        mocked_post.return_value.json.return_value = {"token": "arriba"}
        mocker.patch("shared.github.get_pem", return_value=fake_private_key)
        assert get_github_integration_token(service, integration_id) == "arriba"
        mocked_post.assert_called_with(
            f"{api_url}/app/installations/1/access_tokens",
            headers={
                "Accept": "application/vnd.github.machine-man-preview+json",
                "Authorization": mocker.ANY,
                "User-Agent": "Codecov",
                "Host": "api.github.com",
            },
        )
        after = REGISTRY.get_sample_value(
            "git_provider_api_calls_github_total",
            labels={"endpoint": "get_github_integration_token"},
        )
        e_after = REGISTRY.get_sample_value(
            "git_provider_api_calls_github_enterprise_total",
            labels={"endpoint": "get_github_integration_token"},
        )
        assert after - before == 1
        assert e_after - e_before == 0

    def test_get_github_integration_token_not_found(self, mocker, mock_configuration):
        before = REGISTRY.get_sample_value(
            "git_provider_api_calls_github_total",
            labels={"endpoint": "get_github_integration_token"},
        )
        e_before = REGISTRY.get_sample_value(
            "git_provider_api_calls_github_enterprise_total",
            labels={"endpoint": "get_github_integration_token"},
        )
        service = "github"
        mock_configuration._params["github_enterprise"] = {"url": "http://legit-github"}
        integration_id = 1
        mocked_post = mocker.patch("shared.github.requests.post")
        mocked_post.return_value.status_code = 404
        mocker.patch("shared.github.get_pem", return_value=fake_private_key)
        with pytest.raises(InvalidInstallationError) as exp:
            get_github_integration_token(service, integration_id)
        assert exp.value.error_cause == "installation_not_found"
        mocked_post.assert_called_with(
            "https://api.github.com/app/installations/1/access_tokens",
            headers={
                "Accept": "application/vnd.github.machine-man-preview+json",
                "Authorization": mocker.ANY,
                "User-Agent": "Codecov",
            },
        )
        after = REGISTRY.get_sample_value(
            "git_provider_api_calls_github_total",
            labels={"endpoint": "get_github_integration_token"},
        )
        e_after = REGISTRY.get_sample_value(
            "git_provider_api_calls_github_enterprise_total",
            labels={"endpoint": "get_github_integration_token"},
        )
        assert after - before == 1
        assert e_after - e_before == 0

    def test_get_github_integration_token_unauthorized(
        self, mocker, mock_configuration
    ):
        before = REGISTRY.get_sample_value(
            "git_provider_api_calls_github_total",
            labels={"endpoint": "get_github_integration_token"},
        )
        e_before = REGISTRY.get_sample_value(
            "git_provider_api_calls_github_enterprise_total",
            labels={"endpoint": "get_github_integration_token"},
        )
        service = "github"
        mock_configuration._params["github_enterprise"] = {"url": "http://legit-github"}
        integration_id = 1
        mocked_post = mocker.patch("shared.github.requests.post")
        mocked_post.return_value.status_code = 403
        mocked_post.return_value.json.return_value = {
            "message": "This installation has been suspended",
            "documentation_url": "https://docs.github.com/rest/reference/apps#create-an-installation-access-token-for-an-app",
        }
        mocker.patch("shared.github.get_pem", return_value=fake_private_key)
        with pytest.raises(InvalidInstallationError) as exp:
            get_github_integration_token(service, integration_id)
        assert exp.value.error_cause == "permission_error"
        mocked_post.assert_called_with(
            "https://api.github.com/app/installations/1/access_tokens",
            headers={
                "Accept": "application/vnd.github.machine-man-preview+json",
                "Authorization": mocker.ANY,
                "User-Agent": "Codecov",
            },
        )
        after = REGISTRY.get_sample_value(
            "git_provider_api_calls_github_total",
            labels={"endpoint": "get_github_integration_token"},
        )
        e_after = REGISTRY.get_sample_value(
            "git_provider_api_calls_github_enterprise_total",
            labels={"endpoint": "get_github_integration_token"},
        )
        assert after - before == 1
        assert e_after - e_before == 0

    def test_mark_installation_as_rate_limited(self, mocker):
        mock_redis = MagicMock(name="fake_redis")
        INSTALLATION_ID = 1000
        APP_ID = 250
        mark_installation_as_rate_limited(mock_redis, INSTALLATION_ID, 10, app_id=250)
        mock_redis.set.assert_called_with(
            name=f"rate_limited_installations_{APP_ID}_{INSTALLATION_ID}",
            value=1,
            ex=10,
        )
        mark_installation_as_rate_limited(mock_redis, INSTALLATION_ID, 10, app_id=None)
        mock_redis.set.assert_called_with(
            name=f"rate_limited_installations_default_app_{INSTALLATION_ID}",
            value=1,
            ex=10,
        )

    def test_mark_installation_as_rate_limited_error(self, mocker):
        mock_redis = MagicMock(name="fake_redis")
        mock_redis.set.side_effect = RedisError
        INSTALLATION_ID = 1000
        APP_ID = 250
        # This actually asserts that the error is not raised
        # Despite the call failing
        mark_installation_as_rate_limited(
            mock_redis, INSTALLATION_ID, 10, app_id=APP_ID
        )
        mock_redis.set.assert_called_with(
            name=f"rate_limited_installations_{APP_ID}_{INSTALLATION_ID}",
            value=1,
            ex=10,
        )

    def test_mark_installation_as_rate_limited_ttl_zero(self, mocker):
        mock_redis = MagicMock(name="fake_redis")
        mock_redis.set.side_effect = RedisError
        INSTALLATION_ID = 1000
        APP_ID = 250
        # This actually asserts that the error is not raised
        # Despite the call failing
        mark_installation_as_rate_limited(mock_redis, INSTALLATION_ID, 0, app_id=APP_ID)
        mock_redis.set.assert_not_called()

    def test_is_installation_rate_limited(self, mocker):
        mock_redis = MagicMock(name="fake_redis")
        keys_in_redis = {
            "rate_limited_installations_250_999": 1,
            "rate_limited_installations_default_app_999": 1,
        }

        def exists(key):
            return key in keys_in_redis

        mock_redis.exists.side_effect = exists
        assert is_installation_rate_limited(mock_redis, 1000, 250) == False
        assert is_installation_rate_limited(mock_redis, 999, 250) == True
        assert is_installation_rate_limited(mock_redis, 999) == True
        assert is_installation_rate_limited(mock_redis, 999, app_id=None) == True
        assert is_installation_rate_limited(mock_redis, 999, 200) == False

    def test_is_installation_rate_limited_error(self, mocker):
        mock_redis = MagicMock(name="fake_redis")
        mock_redis.exists.side_effect = RedisError
        assert is_installation_rate_limited(mock_redis, 1000, 250) == False
        assert is_installation_rate_limited(mock_redis, 999, 250) == False
        assert is_installation_rate_limited(mock_redis, 999, 200) == False
