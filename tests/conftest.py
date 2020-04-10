from pathlib import Path

import pytest
import vcr

from shared.config import ConfigHelper


@pytest.fixture
def mock_configuration(mocker):
    m = mocker.patch("shared.config._get_config_instance")
    mock_config = ConfigHelper()
    m.return_value = mock_config
    our_config = {
        "bitbucket": {"bot": {"username": "codecov-io"}},
        "services": {
            "minio": {
                "access_key_id": "codecov-default-key",
                "bucket": "archive",
                "hash_key": "88f572f4726e4971827415efa8867978",
                "periodic_callback_ms": False,
                "secret_access_key": "codecov-default-secret",
                "verify_ssl": False,
            },
            "redis_url": "redis://redis:@localhost:6379/",
        },
        "setup": {
            "codecov_url": "https://codecov.io",
            "encryption_secret": "zp^P9*i8aR3",
        },
    }
    mock_config.set_params(our_config)
    return mock_config


@pytest.fixture
def codecov_vcr(request):
    current_path = Path(request.node.fspath)
    current_path_name = current_path.name.replace(".py", "")
    cls_name = request.node.cls.__name__
    cassete_path = current_path.parent / "cassetes" / current_path_name / cls_name
    current_name = request.node.name
    casset_file_path = str(cassete_path / f"{current_name}.yaml")
    with vcr.use_cassette(
        casset_file_path,
        filter_headers=["authorization"],
        match_on=["method", "scheme", "host", "port", "path"],
    ) as cassete_maker:
        yield cassete_maker


@pytest.fixture
def mock_storage(mocker):
    m = mocker.patch("covreports.storage.MinioStorageService")
    redis_server = mocker.MagicMock()
    m.return_value = redis_server
    yield redis_server
