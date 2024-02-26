from time import time
from unittest.mock import patch

import pytest
from freezegun import freeze_time

# This import here avoids a circular import issue
import shared.torngit
from shared.github import get_github_jwt_token, get_pem
from shared.utils.test_utils import mock_config_helper


@patch("shared.github.load_pem_from_path")
def test_get_pem_from_name(mock_load_pem, mocker):
    configs = {}
    file_configs = {"github.integration.pem": "--------BEGIN RSA PRIVATE KEY-----..."}
    mock_config_helper(mocker, configs, file_configs)
    assert get_pem(pem_name="github") == "--------BEGIN RSA PRIVATE KEY-----..."
    mock_load_pem.assert_not_called()


def test_get_pem_from_path(mocker):
    configs = {}
    file_configs = {"yaml.path.to.pem": "--------BEGIN RSA PRIVATE KEY-----..."}
    mock_config_helper(mocker, configs, file_configs)
    assert (
        get_pem(pem_path="yaml+file://yaml.path.to.pem")
        == "--------BEGIN RSA PRIVATE KEY-----..."
    )


def test_get_pem_from_nowhere():
    with pytest.raises(Exception) as exp:
        get_pem()
    assert exp.exconly() == "Exception: No PEM provided to get installation token"


def test_get_pem_from_path_unknown_schema():
    with pytest.raises(Exception) as exp:
        get_pem(pem_path="unknown_schema://some_path")
    assert exp.exconly() == "Exception: Unknown schema to load PEM"


@freeze_time("2024-02-21T00:00:00")
@patch("shared.github.jwt")
def test_get_github_jwt_token(mock_jwt, mocker):
    mock_jwt.encode.return_value = "encoded_jwt"
    configs = {"github.integration.id": 15000, "github.integration.expires": 300}
    file_configs = {"github.integration.pem": "--------BEGIN RSA PRIVATE KEY-----..."}
    mock_config_helper(mocker, configs, file_configs)
    token = get_github_jwt_token("github")
    assert token == "encoded_jwt"
    mock_jwt.encode.assert_called_with(
        {
            "iat": int(time()),
            "exp": int(time()) + 300,
            "iss": 15000,
        },
        "--------BEGIN RSA PRIVATE KEY-----...",
        algorithm="RS256",
    )
