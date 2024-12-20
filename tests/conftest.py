from pathlib import Path

import pytest
import vcr

from shared.config import ConfigHelper
from shared.reports.resources import (
    LineSession,
    Report,
    ReportFile,
    ReportLine,
    Session,
)


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
    cassette_path = current_path.parent / "cassetes" / current_path_name / cls_name
    current_name = request.node.name
    cassette_file_path = str(cassette_path / f"{current_name}.yaml")
    with vcr.use_cassette(
        cassette_file_path,
        filter_headers=["authorization"],
        filter_query_parameters=["oauth_nonce", "oauth_timestamp", "oauth_signature"],
        record_mode="once",
        match_on=["method", "scheme", "host", "port", "path", "query"],
    ) as cassete_maker:
        yield cassete_maker


@pytest.fixture
def mock_storage(mocker):
    m = mocker.patch("covreports.storage.MinioStorageService")
    redis_server = mocker.MagicMock()
    m.return_value = redis_server
    yield redis_server


@pytest.fixture
def sample_report():
    report = Report()
    first_file = ReportFile("file_1.go")
    second_file = ReportFile("file_2.go")
    third_file = ReportFile("location/file_1.py")
    first_file.append(
        1,
        ReportLine.create(
            coverage=1,
            sessions=[LineSession(0, 1), LineSession(1, 1), LineSession(2, 1)],
        ),
    )
    first_file.append(
        2,
        ReportLine.create(coverage=1, sessions=[LineSession(0, 0), LineSession(1, 1)]),
    )
    first_file.append(
        3,
        ReportLine.create(coverage=1, sessions=[LineSession(0, 1), LineSession(1, 0)]),
    )
    first_file.append(
        5,
        ReportLine.create(coverage=0, sessions=[LineSession(0, 0), LineSession(1, 0)]),
    )
    first_file.append(
        6,
        ReportLine.create(
            coverage="1/2",
            sessions=[LineSession(0, "1/2"), LineSession(1, 0), LineSession(2, "1/4")],
        ),
    )
    second_file.append(12, ReportLine.create(coverage=1, sessions=[[0, 1]]))
    second_file.append(
        51, ReportLine.create(coverage="1/2", type="b", sessions=[[0, "1/2"]])
    )
    third_file.append(
        100, ReportLine.create(coverage="1/2", type="b", sessions=[[3, "1/2"]])
    )
    third_file.append(
        101,
        ReportLine.create(coverage="1/2", type="b", sessions=[[2, "1/2"], [3, "1/2"]]),
    )
    report.append(first_file)
    report.append(second_file)
    report.append(third_file)
    report.add_session(Session(id=0, flags=["simple"]))
    report.add_session(Session(id=1, flags=["complex"]))
    report.add_session(Session(id=2, flags=["complex", "simple"]))
    report.add_session(Session(id=3, flags=[]))
    # TODO manually fix Session totals because the defautl logic doesn't
    return report
