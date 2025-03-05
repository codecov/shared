import json
from base64 import b16encode
from hashlib import md5

import pytest

from shared.api_archive.archive import ArchiveService, MinioEndpoints
from shared.config import ConfigHelper
from shared.django_apps.core.tests.factories import RepositoryFactory
from shared.utils.ReportEncoder import ReportEncoder

pytestmark = pytest.mark.django_db


class TestMinioEndpoints:
    def test_get_path(self):
        path = MinioEndpoints.chunks.get_path(
            version="v4", repo_hash="abc123", commitid="def456"
        )
        assert path == "v4/repos/abc123/commits/def456/chunks.txt"

        path = MinioEndpoints.json_data.get_path(
            version="v4",
            repo_hash="abc123",
            commitid="def456",
            table="coverage",
            field="totals",
            external_id="789",
        )
        assert (
            path == "v4/repos/abc123/commits/def456/json_data/coverage/totals/789.json"
        )

        path = MinioEndpoints.raw.get_path(
            date="2023-01-01",
            repo_hash="abc123",
            commit_sha="def456",
            reportid="report123",
        )
        assert path == "v4/raw/2023-01-01/abc123/def456/report123.txt"


@pytest.fixture
def mock_config(mocker):
    m = mocker.patch("shared.config._get_config_instance")
    mock_config = ConfigHelper()
    m.return_value = mock_config
    our_config = {
        "services": {
            "minio": {
                "host": "minio",
                "access_key_id": "codecov-default-key",
                "bucket": "test-bucket",
                "ttl": "30",
                "hash_key": "test-key",
                "secret_access_key": "codecov-default-secret",
                "verify_ssl": False,
                "port": "9000",
            },
        },
    }
    mock_config.set_params(our_config)

    return mock_config


@pytest.fixture
def mock_repo(mocker):
    repo = RepositoryFactory(repoid=12345)
    repo.author.service = "github"
    return repo


@pytest.fixture
def archive_service(mock_config, mock_repo):
    a = ArchiveService(mock_repo)
    try:
        a.storage.create_root_storage("test-bucket")
    except Exception:
        pass
    return a


class TestArchiveService:
    def test_init(self, archive_service):
        assert archive_service.root == "test-bucket"
        assert archive_service.ttl == 30
        assert archive_service.storage_hash is not None

    def test_init_with_custom_ttl(self, mock_repo):
        archive_service = ArchiveService(mock_repo, ttl=60)
        assert archive_service.ttl == 60

    def test_get_archive_hash(self, mock_config, mock_repo):
        result = ArchiveService.get_archive_hash(mock_repo)
        val = f"{mock_repo.repoid}{mock_repo.service}{mock_repo.service_id}test-key".encode()
        assert result == b16encode(md5(val).digest()).decode()

    def test_write_file(self, mock_config, archive_service):
        archive_service.write_file("test/path", "test data")

        result = archive_service.read_file("test/path")
        assert result == "test data"

    def test_delete_file(self, mock_config, archive_service):
        archive_service.write_file("test/path", "test data")

        archive_service.delete_file("test/path")

        with pytest.raises(Exception):
            archive_service.read_file("test/path")

    def test_read_chunks(self, mock_config, archive_service):
        expected_path = MinioEndpoints.chunks.get_path(
            version="v4", repo_hash=archive_service.storage_hash, commitid="commit123"
        )
        archive_service.write_file(expected_path, "chunk data")

        result = archive_service.read_chunks("commit123")

        assert result == "chunk data"

    def test_read_chunks_no_hash(self, mocker):
        mock_get_config = mocker.patch("shared.api_archive.archive.get_config")
        mock_get_config.side_effect = lambda *args, default=None: {
            ("services", "minio", "bucket"): "test-bucket",
            ("services", "minio", "ttl"): "30",
        }.get(args, default)

        mocker.patch(
            "shared.api_archive.archive.shared.storage.get_appropriate_storage_service",
        )

        archive_service = ArchiveService(None)

        with pytest.raises(ValueError):
            archive_service.read_chunks("commit123")

    def test_create_presigned_put(self, mock_config, archive_service):
        result = archive_service.create_presigned_put("test/path")

        assert isinstance(result, str)
        assert len(result) > 0

    def test_write_json_data_to_storage_with_commit(self, mock_config, archive_service):
        data = {"key": "value"}

        path = archive_service.write_json_data_to_storage(
            "commit123", "table1", "field1", "external1", data
        )

        expected_path = MinioEndpoints.json_data.get_path(
            version="v4",
            repo_hash=archive_service.storage_hash,
            commitid="commit123",
            table="table1",
            field="field1",
            external_id="external1",
        )
        assert path == expected_path

        result = archive_service.read_file(path)
        expected_data = json.dumps(data, cls=ReportEncoder)
        assert result == expected_data

    def test_write_json_data_to_storage_without_commit(
        self, mock_config, archive_service
    ):
        data = {"key": "value"}

        path = archive_service.write_json_data_to_storage(
            None, "table1", "field1", "external1", data
        )

        expected_path = MinioEndpoints.json_data_no_commit.get_path(
            version="v4",
            repo_hash=archive_service.storage_hash,
            table="table1",
            field="field1",
            external_id="external1",
        )
        assert path == expected_path

        result = archive_service.read_file(path)
        expected_data = json.dumps(data, cls=ReportEncoder)
        assert result == expected_data

    def test_write_json_data_to_storage_no_hash(self, mocker):
        mock_get_config = mocker.patch("shared.api_archive.archive.get_config")
        mock_get_config.side_effect = lambda *args, default=None: {
            ("services", "minio", "bucket"): "test-bucket",
            ("services", "minio", "ttl"): "30",
        }.get(args, default)

        mocker.patch(
            "shared.api_archive.archive.shared.storage.get_appropriate_storage_service",
        )

        archive_service = ArchiveService(None)

        with pytest.raises(ValueError):
            archive_service.write_json_data_to_storage(
                "commit123", "table1", "field1", "external1", {"key": "value"}
            )

    def test_write_json_data_to_storage_custom_encoder(
        self, mocker, mock_config, archive_service
    ):
        mock_json_dumps = mocker.patch("json.dumps")
        mock_json_dumps.return_value = '{"key": "value"}'

        data = {"key": "value"}

        class CustomEncoder(ReportEncoder):
            pass

        path = archive_service.write_json_data_to_storage(
            "commit123", "table1", "field1", "external1", data, encoder=CustomEncoder
        )

        mock_json_dumps.assert_called_once_with(data, cls=CustomEncoder)

        result = archive_service.read_file(path)

        assert result == '{"key": "value"}'
