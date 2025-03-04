import pickle
import sys
from unittest.mock import MagicMock, patch

import pytest

from shared.django_apps.core.models import Commit
from shared.reports.api_report_service import (
    SerializableReport,
    build_report_from_commit,
)
from shared.storage.exceptions import FileNotInStorageError


@pytest.fixture
def mock_commit():
    commit = MagicMock(spec=Commit)
    commit.report = {
        "files": {
            "awesome/__init__.py": [
                2,
                [0, 10, 8, 2, 0, "80.00000", 0, 0, 0, 0, 0, 0, 0],
                [[0, 10, 8, 2, 0, "80.00000", 0, 0, 0, 0, 0, 0, 0]],
                [0, 2, 1, 1, 0, "50.00000", 0, 0, 0, 0, 0, 0, 0],
            ],
            "tests/__init__.py": [
                0,
                [0, 3, 2, 1, 0, "66.66667", 0, 0, 0, 0, 0, 0, 0],
                [[0, 3, 2, 1, 0, "66.66667", 0, 0, 0, 0, 0, 0, 0]],
                None,
            ],
            "tests/test_sample.py": [
                1,
                [0, 7, 7, 0, 0, "100", 0, 0, 0, 0, 0, 0, 0],
                [[0, 7, 7, 0, 0, "100", 0, 0, 0, 0, 0, 0, 0]],
                None,
            ],
        },
        "sessions": {
            "0": {
                "N": None,
                "a": "v4/raw/2019-01-10/4434BC2A2EC4FCA57F77B473D83F928C/abf6d4df662c47e32460020ab14abf9303581429/9ccc55a1-8b41-4bb1-a946-ee7a33a7fb56.txt",
                "c": None,
                "d": 1547084427,
                "e": None,
                "f": ["unit"],
                "j": None,
                "n": None,
                "p": None,
                "t": [3, 20, 17, 3, 0, "85.00000", 0, 0, 0, 0, 0, 0, 0],
                "": None,
            },
        },
    }
    commit.totals = {"coverage": 85.5}
    commit.repository_id = "test_repo"
    commit.commitid = "abc123"
    return commit


@pytest.fixture
def mock_chunks():
    return [b"{}\n", b"{}\n"]


@pytest.fixture
def mock_get_config_cache_enabled(mock_get_config):
    def side_effect(*args, **kwargs):
        if (
            len(args) == 3
            and args[0] == "setup"
            and args[1] == "report_service"
            and args[2] == "cache_enabled"
        ):
            return True
        if (
            len(args) == 3
            and args[0] == "setup"
            and args[1] == "report_service"
            and args[2] == "cache_timeout"
        ):
            return 3600

    mock_get_config.side_effect = side_effect
    return mock_get_config


def test_returns_none_when_no_report(mock_commit):
    mock_commit.report = None
    assert build_report_from_commit(mock_commit) is None


def test_returns_none_when_chunks_not_found(mock_commit):
    with patch("shared.reports.api_report_service.ArchiveService") as MockArchive:
        MockArchive.return_value.read_chunks.side_effect = FileNotInStorageError()
        assert build_report_from_commit(mock_commit) is None


def test_builds_report_successfully(mock_commit, mock_chunks):
    with patch("shared.reports.api_report_service.ArchiveService") as MockArchive:
        MockArchive.return_value.read_chunks.return_value = mock_chunks

        report = build_report_from_commit(mock_commit)

        assert isinstance(report, SerializableReport)
        MockArchive.return_value.read_chunks.assert_called_once_with(
            mock_commit.commitid
        )


@patch("shared.reports.api_report_service.get_config")
def test_caching_disabled_by_default(mock_get_config, mock_commit, mock_chunks):
    mock_get_config.return_value = False

    with (
        patch("shared.reports.api_report_service.ArchiveService") as MockArchive,
        patch("shared.reports.api_report_service.cache") as mock_cache,
    ):
        MockArchive.return_value.read_chunks.return_value = mock_chunks
        build_report_from_commit(mock_commit)

        MockArchive.return_value.read_file.assert_not_called()
        MockArchive.return_value.write_file.assert_not_called()
        mock_cache.get.assert_not_called()
        mock_cache.set.assert_not_called()


@patch("shared.reports.api_report_service.get_config")
def test_uses_archive_when_redis_cache_exists(
    mock_get_config_cache_enabled, mock_commit
):
    cached_report = SerializableReport.from_chunks([], {}, {}, {})
    cached_bytes = pickle.dumps(cached_report)

    with (
        patch("shared.reports.api_report_service.ArchiveService") as MockArchive,
        patch("shared.reports.api_report_service.cache") as mock_cache,
    ):
        mock_cache.get.return_value = "cached"  # Redis has the key
        MockArchive.return_value.read_file.return_value = cached_bytes

        result = build_report_from_commit(mock_commit)

        assert result.__class__ == cached_report.__class__
        redis_key = f"report:{mock_commit.repository_id}:{mock_commit.commitid}"
        mock_cache.get.assert_called_once_with(redis_key)
        cache_key = f"reports/cache/{mock_commit.commitid}/SerializableReport"
        MockArchive.return_value.read_file.assert_called_once_with(cache_key)
        mock_cache.set.assert_not_called()


@patch("shared.reports.api_report_service.get_config")
def test_skips_archive_when_redis_cache_missing(
    mock_get_config_cache_enabled, mock_commit, mock_chunks
):
    with (
        patch("shared.reports.api_report_service.ArchiveService") as MockArchive,
        patch("shared.reports.api_report_service.cache") as mock_cache,
    ):
        mock_cache.get.return_value = None  # Redis cache miss
        MockArchive.return_value.read_chunks.return_value = mock_chunks

        report = build_report_from_commit(mock_commit)

        redis_key = f"report:{mock_commit.repository_id}:{mock_commit.commitid}"
        mock_cache.get.assert_called_once_with(redis_key)
        MockArchive.return_value.read_file.assert_not_called()
        assert isinstance(report, SerializableReport)


@patch("shared.reports.api_report_service.get_config")
def test_caches_new_report(mock_get_config_cache_enabled, mock_commit, mock_chunks):
    with (
        patch("shared.reports.api_report_service.ArchiveService") as MockArchive,
        patch("shared.reports.api_report_service.cache") as mock_cache,
    ):
        mock_cache.get.return_value = None
        MockArchive.return_value.read_chunks.return_value = mock_chunks

        report = build_report_from_commit(mock_commit)

        cache_key = f"reports/cache/{mock_commit.commitid}/SerializableReport"

        MockArchive.return_value.write_file.assert_called_once_with(
            cache_key, pickle.dumps(report)
        )


@patch("shared.reports.api_report_service.get_config")
def test_handles_archive_cache_write_failure(
    mock_get_config_cache_enabled, mock_commit, mock_chunks
):
    with (
        patch("shared.reports.api_report_service.ArchiveService") as MockArchive,
        patch("shared.reports.api_report_service.cache") as mock_cache,
    ):
        mock_cache.get.return_value = None
        MockArchive.return_value.read_chunks.return_value = mock_chunks
        MockArchive.return_value.write_file.side_effect = Exception("Storage error")

        report = build_report_from_commit(mock_commit)

        # Should still return report even if caching fails
        assert isinstance(report, SerializableReport)
        # Redis cache should not be set if archive fails
        mock_cache.set.assert_not_called()


def test_records_report_size(mock_commit, mock_chunks):
    with (
        patch("shared.reports.api_report_service.ArchiveService") as MockArchive,
        patch("shared.reports.api_report_service.report_size_gauge") as mock_gauge,
    ):
        mock_labels = MagicMock()
        mock_gauge.labels.return_value = mock_labels

        MockArchive.return_value.read_chunks.return_value = mock_chunks
        report = build_report_from_commit(mock_commit)

        mock_gauge.labels.assert_called_once_with(report_type=report.__class__.__name__)
        mock_labels.set.assert_called_once_with(sys.getsizeof(report))
