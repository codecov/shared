from pathlib import Path
from typing import Tuple
from unittest.mock import patch

import pytest
from sqlalchemy.orm import Session as DbSession

from shared.bundle_analysis import BundleAnalysisReport, BundleAnalysisReportLoader
from shared.bundle_analysis.models import (
    SCHEMA_VERSION,
    Asset,
    AssetType,
    Bundle,
    Chunk,
    MetadataKey,
    Module,
    Session,
)
from shared.storage.exceptions import PutRequestRateLimitError
from shared.storage.memory import MemoryStorageService

sample_bundle_stats_path = (
    Path(__file__).parent.parent.parent / "samples" / "sample_bundle_stats.json"
)

sample_bundle_stats_path_2 = (
    Path(__file__).parent.parent.parent / "samples" / "sample_bundle_stats_other.json"
)

sample_bundle_stats_path_3 = (
    Path(__file__).parent.parent.parent
    / "samples"
    / "sample_bundle_stats_invalid_name.json"
)

sample_bundle_stats_path_4 = (
    Path(__file__).parent.parent.parent / "samples" / "sample_bundle_stats_v1.json"
)

sample_bundle_stats_path_5 = (
    Path(__file__).parent.parent.parent
    / "samples"
    / "sample_bundle_stats_another_bundle.json"
)


def _table_rows_count(db_session: DbSession) -> Tuple[int]:
    return (
        db_session.query(Bundle).count(),
        db_session.query(Session).count(),
        db_session.query(Asset).count(),
        db_session.query(Chunk).count(),
        db_session.query(Module).count(),
    )


def test_create_bundle_report():
    try:
        report = BundleAnalysisReport()
        session_id = report.ingest(sample_bundle_stats_path)
        assert session_id == 1

        assert report.metadata() == {
            MetadataKey.SCHEMA_VERSION: SCHEMA_VERSION,
        }

        bundle_reports = list(report.bundle_reports())
        assert len(bundle_reports) == 1

        bundle_report = report.bundle_report("invalid")
        assert bundle_report is None
        bundle_report = report.bundle_report("sample")

        asset_reports = list(bundle_report.asset_reports())

        assert [
            (
                ar.name,
                ar.hashed_name,
                ar.size,
                ar.gzip_size,
                len(ar.modules()),
                ar.asset_type,
            )
            for ar in asset_reports
        ] == [
            (
                "assets/react-*.svg",
                "assets/react-35ef61ed.svg",
                4126,
                4125,
                0,
                AssetType.IMAGE,
            ),
            (
                "assets/index-*.css",
                "assets/index-d526a0c5.css",
                1421,
                1420,
                0,
                AssetType.STYLESHEET,
            ),
            (
                "assets/LazyComponent-*.js",
                "assets/LazyComponent-fcbb0922.js",
                294,
                293,
                1,
                AssetType.JAVASCRIPT,
            ),
            (
                "assets/index-*.js",
                "assets/index-c8676264.js",
                154,
                153,
                2,
                AssetType.JAVASCRIPT,
            ),
            # FIXME: this is wrong since it's capturing the SVG and CSS modules as well.
            # Made a similar note in the parser code where the associations are made
            (
                "assets/index-*.js",
                "assets/index-666d2e09.js",
                144577,
                144576,
                28,
                AssetType.JAVASCRIPT,
            ),
        ]

        for ar in asset_reports:
            for module in ar.modules():
                assert isinstance(module.name, str)
                assert isinstance(module.size, int)

        assert bundle_report.total_size() == 150572
        assert report.session_count() == 1
    finally:
        report.cleanup()


def test_bundle_report_asset_filtering():
    try:
        report = BundleAnalysisReport()
        session_id = report.ingest(sample_bundle_stats_path)
        assert session_id == 1

        assert report.metadata() == {
            MetadataKey.SCHEMA_VERSION: SCHEMA_VERSION,
        }

        bundle_reports = list(report.bundle_reports())
        assert len(bundle_reports) == 1

        bundle_report = report.bundle_report("invalid")
        assert bundle_report is None
        bundle_report = report.bundle_report("sample")

        all_asset_reports = list(bundle_report.asset_reports())
        assert len(all_asset_reports) == 5

        filtered_asset_reports = list(
            bundle_report.asset_reports(
                asset_types=[AssetType.JAVASCRIPT],
                chunk_entry=True,
                chunk_initial=True,
            )
        )

        for ar in filtered_asset_reports:
            for module in ar.modules():
                assert isinstance(module.name, str)
                assert isinstance(module.size, int)

        assert len(filtered_asset_reports) == 1
        assert (
            bundle_report.total_size(
                asset_types=[AssetType.JAVASCRIPT],
                chunk_entry=True,
                chunk_initial=True,
            )
            == 144577
        )

    finally:
        report.cleanup()


def test_save_load_bundle_report():
    try:
        report = BundleAnalysisReport()
        report.ingest(sample_bundle_stats_path)

        loader = BundleAnalysisReportLoader(
            storage_service=MemoryStorageService({}),
            repo_key="testing",
        )
        test_key = "8d1099f1-ba73-472f-957f-6908eced3f42"
        loader.save(report, test_key)

        db_path = report.db_path
        report = loader.load(test_key)

        initial_data = open(db_path, "rb").read()
        loaded_data = open(report.db_path, "rb").read()

        assert db_path != report.db_path
        assert len(initial_data) > 0
        assert initial_data == loaded_data
    finally:
        report.cleanup()


def test_reupload_bundle_report():
    try:
        report = BundleAnalysisReport()

        # Upload the first stats file
        report.ingest(sample_bundle_stats_path)

        assert report.metadata() == {
            MetadataKey.SCHEMA_VERSION: SCHEMA_VERSION,
        }

        bundle_reports = list(report.bundle_reports())
        assert len(bundle_reports) == 1

        bundle_report = report.bundle_report("sample")

        assert bundle_report.total_size() == 150572
        assert report.session_count() == 1

        # Re-upload another file of the same name, it should fully replace the previous
        report.ingest(sample_bundle_stats_path_2)

        assert report.metadata() == {
            MetadataKey.SCHEMA_VERSION: SCHEMA_VERSION,
        }

        bundle_reports = list(report.bundle_reports())
        assert len(bundle_reports) == 1

        bundle_report = report.bundle_report("sample")

        assert bundle_report.total_size() == 151672
        assert report.session_count() == 1
    finally:
        report.cleanup()


def test_bundle_report_no_assets():
    report_path = (
        Path(__file__).parent.parent.parent
        / "samples"
        / "sample_bundle_stats_no_assets.json"
    )
    report = BundleAnalysisReport()
    report.ingest(report_path)
    bundle_report = report.bundle_report("b5")
    asset_reports = list(bundle_report.asset_reports())

    assert asset_reports == []
    assert bundle_report.total_size() == 0


def test_bundle_report_no_chunks():
    report_path = (
        Path(__file__).parent.parent.parent
        / "samples"
        / "sample_bundle_stats_no_chunks.json"
    )
    report = BundleAnalysisReport()
    report.ingest(report_path)
    bundle_report = report.bundle_report("sample")
    asset_reports = list(bundle_report.asset_reports())

    assert len(asset_reports) == 2
    assert bundle_report.total_size() == 144731


def test_bundle_report_no_modules():
    report_path = (
        Path(__file__).parent.parent.parent
        / "samples"
        / "sample_bundle_stats_no_modules.json"
    )
    report = BundleAnalysisReport()
    report.ingest(report_path)
    bundle_report = report.bundle_report("sample")
    asset_reports = list(bundle_report.asset_reports())

    assert len(asset_reports) == 2
    assert bundle_report.total_size() == 144731


def test_bundle_report_info():
    report = BundleAnalysisReport()
    report.ingest(sample_bundle_stats_path)
    bundle_report = report.bundle_report("sample")
    bundle_report_info = bundle_report.info()

    assert bundle_report_info["version"] == "2"
    assert bundle_report_info["bundler_name"] == "rollup"
    assert bundle_report_info["bundler_version"] == "3.29.4"
    assert bundle_report_info["built_at"] == 1701451048604
    assert bundle_report_info["plugin_name"] == "codecov-vite-bundle-analysis-plugin"
    assert bundle_report_info["plugin_version"] == "1.0.0"
    assert bundle_report_info["duration"] == 331


def test_bundle_report_size_integer():
    report_path = (
        Path(__file__).parent.parent.parent
        / "samples"
        / "sample_bundle_stats_decimal_size.json"
    )
    report = BundleAnalysisReport()
    report.ingest(report_path)
    bundle_report = report.bundle_report("sample")

    assert bundle_report.total_size() == 150572


def test_bundle_parser_error():
    with patch(
        "shared.bundle_analysis.parsers.ParserV1._parse_assets_event",
        side_effect=Exception("MockError"),
    ):
        report = BundleAnalysisReport()
        with pytest.raises(Exception) as excinfo:
            report.ingest(sample_bundle_stats_path)
            assert (
                excinfo.bundle_analysis_plugin_name
                == "codecov-vite-bundle-analysis-plugin"
            )


def test_bundle_name_not_valid():
    report = BundleAnalysisReport()
    with pytest.raises(Exception) as excinfo:
        report.ingest(sample_bundle_stats_path_3)
        assert (
            excinfo.bundle_analysis_plugin_name == "codecov-vite-bundle-analysis-plugin"
        )


def test_bundle_file_save_rate_limit_error():
    with patch(
        "shared.storage.memory.MemoryStorageService.write_file",
        side_effect=Exception("TooManyRequests"),
    ):
        with pytest.raises(Exception) as excinfo:
            report = BundleAnalysisReport()
            report.ingest(sample_bundle_stats_path)

            loader = BundleAnalysisReportLoader(
                storage_service=MemoryStorageService({}),
                repo_key="testing",
            )
            test_key = "8d1099f1-ba73-472f-957f-6908eced3f42"
            loader.save(report, test_key)

            assert str(excinfo) == "TooManyRequests"
            assert type(excinfo) == PutRequestRateLimitError


def test_bundle_file_save_unknown_error():
    with patch(
        "shared.storage.memory.MemoryStorageService.write_file",
        side_effect=Exception("UnknownError"),
    ):
        with pytest.raises(Exception) as excinfo:
            report = BundleAnalysisReport()
            report.ingest(sample_bundle_stats_path)

            loader = BundleAnalysisReportLoader(
                storage_service=MemoryStorageService({}),
                repo_key="testing",
            )
            test_key = "8d1099f1-ba73-472f-957f-6908eced3f42"
            loader.save(report, test_key)

            assert str(excinfo) == "UnknownError"
            assert type(excinfo) is Exception


def test_create_bundle_report_v1():
    try:
        report = BundleAnalysisReport()
        session_id = report.ingest(sample_bundle_stats_path_4)
        assert session_id == 1

        assert report.metadata() == {
            MetadataKey.SCHEMA_VERSION: SCHEMA_VERSION,
        }

        bundle_reports = list(report.bundle_reports())
        assert len(bundle_reports) == 1

        bundle_report = report.bundle_report("invalid")
        assert bundle_report is None
        bundle_report = report.bundle_report("sample")

        bundle_report_info = bundle_report.info()
        assert bundle_report_info["version"] == "1"

        asset_reports = list(bundle_report.asset_reports())

        assert [
            (
                ar.name,
                ar.hashed_name,
                ar.size,
                ar.gzip_size,
                len(ar.modules()),
                ar.asset_type,
            )
            for ar in asset_reports
        ] == [
            (
                "assets/react-*.svg",
                "assets/react-35ef61ed.svg",
                4126,
                4,
                0,
                AssetType.IMAGE,
            ),
            (
                "assets/index-*.css",
                "assets/index-d526a0c5.css",
                1421,
                1,
                0,
                AssetType.STYLESHEET,
            ),
            (
                "assets/LazyComponent-*.js",
                "assets/LazyComponent-fcbb0922.js",
                294,
                0,
                1,
                AssetType.JAVASCRIPT,
            ),
            (
                "assets/index-*.js",
                "assets/index-c8676264.js",
                154,
                0,
                2,
                AssetType.JAVASCRIPT,
            ),
            # FIXME: this is wrong since it's capturing the SVG and CSS modules as well.
            # Made a similar note in the parser code where the associations are made
            (
                "assets/index-*.js",
                "assets/index-666d2e09.js",
                144577,
                144,
                28,
                AssetType.JAVASCRIPT,
            ),
        ]

        for ar in asset_reports:
            for module in ar.modules():
                assert isinstance(module.name, str)
                assert isinstance(module.size, int)

        assert bundle_report.total_size() == 150572
        assert report.session_count() == 1
    finally:
        report.cleanup()


def test_bundle_is_cached():
    try:
        bundle_analysis_report = BundleAnalysisReport()
        session_id = bundle_analysis_report.ingest(sample_bundle_stats_path)
        assert session_id == 1

        session_id = bundle_analysis_report.ingest(sample_bundle_stats_path_5)
        assert session_id == 2

        assert bundle_analysis_report.metadata() == {
            MetadataKey.SCHEMA_VERSION: SCHEMA_VERSION,
        }

        # When doing ingest (ie when handling a upload), its never cached
        bundle_reports = list(bundle_analysis_report.bundle_reports())
        assert len(bundle_reports) == 2
        for bundle in bundle_reports:
            assert bundle.is_cached() == False
        assert bundle_analysis_report.is_cached() == False

        # Test setting 'sample' bundle to True
        bundle_analysis_report.update_is_cached(data={"sample": True})
        assert bundle_analysis_report.bundle_report("sample").is_cached() == True
        assert bundle_analysis_report.bundle_report("sample2").is_cached() == False
        assert bundle_analysis_report.is_cached() == True

        # Test setting 'sample2' bundle to True and 'sample' back to False
        bundle_analysis_report.update_is_cached(data={"sample2": True, "sample": False})
        assert bundle_analysis_report.bundle_report("sample").is_cached() == False
        assert bundle_analysis_report.bundle_report("sample2").is_cached() == True
        assert bundle_analysis_report.is_cached() == True

    finally:
        bundle_analysis_report.cleanup()


def test_bundle_deletion():
    try:
        bundle_analysis_report = BundleAnalysisReport()
        db_session = bundle_analysis_report.db_session

        session_id = bundle_analysis_report.ingest(sample_bundle_stats_path)
        assert session_id == 1

        session_id = bundle_analysis_report.ingest(sample_bundle_stats_path_5)
        assert session_id == 2

        assert _table_rows_count(db_session) == (2, 2, 10, 6, 62)

        # Delete non-existent bundle
        bundle_analysis_report.delete_bundle_by_name("fake")
        assert _table_rows_count(db_session) == (2, 2, 10, 6, 62)

        # Delete bundle 'sample'
        bundle_analysis_report.delete_bundle_by_name("sample")
        assert _table_rows_count(db_session) == (1, 1, 5, 3, 31)
        res = list(db_session.query(Bundle).all())
        assert len(res) == 1
        assert res[0].name == "sample2"

        # Delete bundle 'sample' again
        bundle_analysis_report.delete_bundle_by_name("sample")
        assert _table_rows_count(db_session) == (1, 1, 5, 3, 31)
        res = list(db_session.query(Bundle).all())
        assert len(res) == 1
        assert res[0].name == "sample2"

        # Delete bundle 'sample2'
        bundle_analysis_report.delete_bundle_by_name("sample2")
        assert _table_rows_count(db_session) == (0, 0, 0, 0, 0)
        res = list(db_session.query(Bundle).all())
        assert len(res) == 0

    finally:
        bundle_analysis_report.cleanup()
