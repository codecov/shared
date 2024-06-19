from pathlib import Path
from unittest.mock import patch

import pytest

from shared.bundle_analysis import BundleAnalysisReport, BundleAnalysisReportLoader
from shared.bundle_analysis.models import AssetType, MetadataKey
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


def test_create_bundle_report():
    try:
        report = BundleAnalysisReport()
        session_id = report.ingest(sample_bundle_stats_path)
        assert session_id == 1

        assert report.metadata() == {
            MetadataKey.SCHEMA_VERSION: 1,
        }

        bundle_reports = list(report.bundle_reports())
        assert len(bundle_reports) == 1

        bundle_report = report.bundle_report("invalid")
        assert bundle_report is None
        bundle_report = report.bundle_report("sample")

        asset_reports = list(bundle_report.asset_reports())

        assert [
            (ar.name, ar.hashed_name, ar.size, len(ar.modules()), ar.asset_type)
            for ar in asset_reports
        ] == [
            (
                "assets/react-*.svg",
                "assets/react-35ef61ed.svg",
                4126,
                0,
                AssetType.IMAGE,
            ),
            (
                "assets/index-*.css",
                "assets/index-d526a0c5.css",
                1421,
                0,
                AssetType.STYLESHEET,
            ),
            (
                "assets/LazyComponent-*.js",
                "assets/LazyComponent-fcbb0922.js",
                294,
                1,
                AssetType.JAVASCRIPT,
            ),
            (
                "assets/index-*.js",
                "assets/index-c8676264.js",
                154,
                2,
                AssetType.JAVASCRIPT,
            ),
            # FIXME: this is wrong since it's capturing the SVG and CSS modules as well.
            # Made a similar note in the parser code where the associations are made
            (
                "assets/index-*.js",
                "assets/index-666d2e09.js",
                144577,
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
            MetadataKey.SCHEMA_VERSION: 1,
        }

        bundle_reports = list(report.bundle_reports())
        assert len(bundle_reports) == 1

        bundle_report = report.bundle_report("invalid")
        assert bundle_report is None
        bundle_report = report.bundle_report("sample")

        all_asset_reports = list(bundle_report.asset_reports())
        assert len(all_asset_reports) == 5

        filtered_asset_reports = list(bundle_report.asset_reports(
            asset_types=[AssetType.JAVASCRIPT],
            chunk_entry=True,
            chunk_initial=True,
        ))

        for ar in filtered_asset_reports:
            for module in ar.modules():
                assert isinstance(module.name, str)
                assert isinstance(module.size, int)

        assert len(filtered_asset_reports) == 1
        assert bundle_report.total_size(
            asset_types=[AssetType.JAVASCRIPT],
            chunk_entry=True,
            chunk_initial=True,
        ) == 144577

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
            MetadataKey.SCHEMA_VERSION: 1,
        }

        bundle_reports = list(report.bundle_reports())
        assert len(bundle_reports) == 1

        bundle_report = report.bundle_report("sample")

        assert bundle_report.total_size() == 150572
        assert report.session_count() == 1

        # Re-upload another file of the same name, it should fully replace the previous
        report.ingest(sample_bundle_stats_path_2)

        assert report.metadata() == {
            MetadataKey.SCHEMA_VERSION: 1,
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

    assert bundle_report_info["version"] == "1"
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
        "shared.bundle_analysis.parser.Parser._parse_assets_event",
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
            assert type(excinfo) == Exception
