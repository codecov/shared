from pathlib import Path
from typing import Tuple
from unittest import TestCase
from unittest.mock import patch

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from shared.bundle_analysis import BundleAnalysisReport, BundleAnalysisReportLoader
from shared.bundle_analysis.models import (
    SCHEMA_VERSION,
    Asset,
    AssetType,
    Bundle,
    Chunk,
    DynamicImport,
    Metadata,
    MetadataKey,
    Module,
    Session,
    get_db_session,
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

sample_bundle_stats_path_6 = (
    Path(__file__).parent.parent.parent
    / "samples"
    / "sample_bundle_stats_asset_routes.json"
)

sample_bundle_stats_path_7 = (
    Path(__file__).parent.parent.parent
    / "samples"
    / "sample_bundle_stats_dynamic_imports_1.json"
)

sample_bundle_stats_path_8 = (
    Path(__file__).parent.parent.parent
    / "samples"
    / "sample_bundle_stats_dynamic_imports_2.json"
)

sample_bundle_stats_path_9 = (
    Path(__file__).parent.parent.parent
    / "samples"
    / "sample_bundle_stats_dynamic_import_routing_1.json"
)

sample_bundle_stats_path_10 = (
    Path(__file__).parent.parent.parent
    / "samples"
    / "sample_bundle_stats_w_bad_chunk.json"
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
        session_id, bundle_name = report.ingest(sample_bundle_stats_path)
        assert session_id == 1
        assert bundle_name == "sample"

        assert report.metadata() == {
            MetadataKey.SCHEMA_VERSION: SCHEMA_VERSION,
        }

        bundle_reports = list(report.bundle_reports())
        assert len(bundle_reports) == 1

        bundle_report = report.bundle_report("invalid")
        assert bundle_report is None
        bundle_report = report.bundle_report("sample")

        # Find an asset by its name
        asset_report_by_name = bundle_report.asset_report_by_name(
            "assets/index-666d2e09.js"
        )
        assert asset_report_by_name.name == "assets/index-*.js"
        assert asset_report_by_name.hashed_name == "assets/index-666d2e09.js"
        assert asset_report_by_name.size == 144577
        assert asset_report_by_name.gzip_size == 144576
        assert len(asset_report_by_name.modules()) == 28
        assert asset_report_by_name.asset_type == AssetType.JAVASCRIPT

        # Find a non existent asset by its name
        asset_report_by_name = bundle_report.asset_report_by_name(
            "assets/doesnotexist.js"
        )
        assert asset_report_by_name is None

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
        session_id, bundle_name = report.ingest(sample_bundle_stats_path)
        assert session_id == 1
        assert bundle_name == "sample"

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


def test_bundle_report_asset_ordering():
    try:
        report = BundleAnalysisReport()
        session_id, bundle_name = report.ingest(sample_bundle_stats_path)
        assert session_id == 1
        assert bundle_name == "sample"

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

        # Sort by size in descending
        ordered_asset_reports = list(
            (ar.name, ar.size)
            for ar in bundle_report.asset_reports(
                ordering_column="size",
                ordering_desc=True,
            )
        )
        assert ordered_asset_reports == [
            ("assets/index-*.js", 144577),
            ("assets/react-*.svg", 4126),
            ("assets/index-*.css", 1421),
            ("assets/LazyComponent-*.js", 294),
            ("assets/index-*.js", 154),
        ]
        # Sort by size in ascending
        ordered_asset_reports = list(
            (ar.name, ar.size)
            for ar in bundle_report.asset_reports(
                ordering_column="size",
                ordering_desc=False,
            )
        )
        assert ordered_asset_reports == [
            ("assets/index-*.js", 154),
            ("assets/LazyComponent-*.js", 294),
            ("assets/index-*.css", 1421),
            ("assets/react-*.svg", 4126),
            ("assets/index-*.js", 144577),
        ]
        # Sort by name in descending
        ordered_asset_reports = list(
            (ar.name, ar.size)
            for ar in bundle_report.asset_reports(
                ordering_column="name",
                ordering_desc=True,
            )
        )
        assert ordered_asset_reports == [
            ("assets/react-*.svg", 4126),
            ("assets/index-*.css", 1421),
            ("assets/index-*.js", 154),
            ("assets/index-*.js", 144577),
            ("assets/LazyComponent-*.js", 294),
        ]
        # Sort by name in ascending
        ordered_asset_reports = list(
            (ar.name, ar.size)
            for ar in bundle_report.asset_reports(
                ordering_column="name",
                ordering_desc=False,
            )
        )
        assert ordered_asset_reports == [
            ("assets/LazyComponent-*.js", 294),
            ("assets/index-*.js", 144577),
            ("assets/index-*.js", 154),
            ("assets/index-*.css", 1421),
            ("assets/react-*.svg", 4126),
        ]
    finally:
        report.cleanup()


def test_bundle_report_asset_routes_supported_plugin():
    try:
        report = BundleAnalysisReport()
        report.ingest(sample_bundle_stats_path_6)

        bundle_report = report.bundle_report("sample")
        all_asset_reports = list(bundle_report.asset_reports())

        EXPECTED_ASSET_ROUTES_MAPPING = {
            "_app/immutable/assets/0.CT0x_Q5c.css": [],
            "_app/immutable/assets/2.Cs8KR-Bb.css": [],
            "_app/immutable/assets/4.DOkkq0IA.css": [],
            "_app/immutable/assets/5.CU6psp88.css": [],
            "_app/immutable/assets/fira-mono-all-400-normal.B2mvLtSD.woff": [],
            "_app/immutable/assets/fira-mono-cyrillic-400-normal.36-45Uyg.woff2": [],
            "_app/immutable/assets/fira-mono-cyrillic-ext-400-normal.B04YIrm4.woff2": [],
            "_app/immutable/assets/fira-mono-greek-400-normal.C3zng6O6.woff2": [],
            "_app/immutable/assets/fira-mono-greek-ext-400-normal.CsqI23CO.woff2": [],
            "_app/immutable/assets/fira-mono-latin-400-normal.DKjLVgQi.woff2": [],
            "_app/immutable/assets/fira-mono-latin-ext-400-normal.D6XfiR-_.woff2": [],
            "_app/immutable/assets/svelte-welcome.0pIiHnVF.webp": [],
            "_app/immutable/assets/svelte-welcome.VNiyy3gC.png": [],
            "_app/immutable/chunks/entry.BaWB2kHj.js": [],
            "_app/immutable/chunks/index.DDRweiI9.js": [],
            "_app/immutable/chunks/index.Ice1EKvx.js": [],
            "_app/immutable/chunks/index.R8ovVqwX.js": [],
            "_app/immutable/chunks/scheduler.Dk-snqIU.js": [],
            "_app/immutable/chunks/stores.BrqGIpx3.js": [],
            "_app/immutable/entry/app.Dd9ByE1Q.js": [],
            "_app/immutable/entry/start.B1Q1eB84.js": [],
            "_app/immutable/nodes/0.CL_S-12h.js": ["/"],
            "_app/immutable/nodes/1.stWWSe4n.js": [],
            "_app/immutable/nodes/2.BMQFqo-e.js": ["/"],
            "_app/immutable/nodes/3.BqQOub2U.js": ["/about"],
            "_app/immutable/nodes/4.CcjRtXvw.js": ["/sverdle"],
            "_app/immutable/nodes/5.CwxmUzn6.js": ["/sverdle/how-to-play"],
            "_app/version.json": [],
        }

        asset_routes_mapping = {}
        for asset_report in all_asset_reports:
            asset_routes_mapping[asset_report.hashed_name] = asset_report.routes()
        tc = TestCase()
        tc.maxDiff = None
        tc.assertDictEqual(EXPECTED_ASSET_ROUTES_MAPPING, asset_routes_mapping)

    finally:
        report.cleanup()


def test_bundle_report_asset_routes_unsupported_plugin():
    try:
        report = BundleAnalysisReport()
        report.ingest(sample_bundle_stats_path)

        bundle_report = report.bundle_report("sample")
        all_asset_reports = list(bundle_report.asset_reports())

        EXPECTED_ASSET_ROUTES_MAPPING = {
            "assets/LazyComponent-fcbb0922.js": None,
            "assets/index-666d2e09.js": None,
            "assets/index-c8676264.js": None,
            "assets/index-d526a0c5.css": None,
            "assets/react-35ef61ed.svg": None,
        }

        asset_routes_mapping = {}
        for asset_report in all_asset_reports:
            asset_routes_mapping[asset_report.hashed_name] = asset_report.routes()
        tc = TestCase()
        tc.maxDiff = None
        tc.assertDictEqual(EXPECTED_ASSET_ROUTES_MAPPING, asset_routes_mapping)

    finally:
        report.cleanup()


def test_save_load_bundle_report():
    try:
        created_report = BundleAnalysisReport()
        created_report.ingest(sample_bundle_stats_path)

        loader = BundleAnalysisReportLoader(
            storage_service=MemoryStorageService({}),
            repo_key="testing",
        )
        test_key = "8d1099f1-ba73-472f-957f-6908eced3f42"
        loader.save(created_report, test_key)

        report = loader.load(test_key)

        initial_data = open(created_report.db_path, "rb").read()
        loaded_data = open(report.db_path, "rb").read()

        assert created_report.db_path != report.db_path
        assert len(initial_data) > 0
        assert initial_data == loaded_data
    finally:
        created_report.cleanup()
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
    try:
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
    finally:
        report.cleanup()


def test_bundle_report_no_chunks():
    try:
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
    finally:
        report.cleanup()


def test_bundle_report_no_modules():
    try:
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
    finally:
        report.cleanup()


def test_bundle_report_info():
    try:
        report = BundleAnalysisReport()
        report.ingest(sample_bundle_stats_path)
        bundle_report = report.bundle_report("sample")
        bundle_report_info = bundle_report.info()

        assert bundle_report_info["version"] == "2"
        assert bundle_report_info["bundler_name"] == "rollup"
        assert bundle_report_info["bundler_version"] == "3.29.4"
        assert bundle_report_info["built_at"] == 1701451048604
        assert (
            bundle_report_info["plugin_name"] == "codecov-vite-bundle-analysis-plugin"
        )
        assert bundle_report_info["plugin_version"] == "1.0.0"
        assert bundle_report_info["duration"] == 331
    finally:
        report.cleanup()


def test_bundle_report_size_integer():
    try:
        report_path = (
            Path(__file__).parent.parent.parent
            / "samples"
            / "sample_bundle_stats_decimal_size.json"
        )
        report = BundleAnalysisReport()
        report.ingest(report_path)
        bundle_report = report.bundle_report("sample")

        assert bundle_report.total_size() == 150572
    finally:
        report.cleanup()


def test_bundle_parser_error():
    with patch(
        "shared.bundle_analysis.parsers.ParserV1._parse_assets_event",
        side_effect=Exception("MockError"),
    ):
        try:
            report = BundleAnalysisReport()
            with pytest.raises(Exception) as excinfo:
                report.ingest(sample_bundle_stats_path)
                assert (
                    excinfo.bundle_analysis_plugin_name
                    == "codecov-vite-bundle-analysis-plugin"
                )
        finally:
            report.cleanup()


def test_bundle_name_not_valid():
    try:
        report = BundleAnalysisReport()
        with pytest.raises(Exception) as excinfo:
            report.ingest(sample_bundle_stats_path_3)
            assert (
                excinfo.bundle_analysis_plugin_name
                == "codecov-vite-bundle-analysis-plugin"
            )
    finally:
        report.cleanup()


def test_bundle_file_save_rate_limit_error():
    with patch(
        "shared.storage.memory.MemoryStorageService.write_file",
        side_effect=Exception("TooManyRequests"),
    ):
        with pytest.raises(Exception) as excinfo:
            try:
                report = BundleAnalysisReport()
                report.ingest(sample_bundle_stats_path)

                loader = BundleAnalysisReportLoader(
                    storage_service=MemoryStorageService({}),
                    repo_key="testing",
                )
                test_key = "8d1099f1-ba73-472f-957f-6908eced3f42"
                loader.save(report, test_key)

                assert str(excinfo) == "TooManyRequests"
                assert isinstance(excinfo, PutRequestRateLimitError)
            finally:
                report.cleanup()


def test_bundle_file_save_unknown_error():
    with patch(
        "shared.storage.memory.MemoryStorageService.write_file",
        side_effect=Exception("UnknownError"),
    ):
        with pytest.raises(Exception) as excinfo:
            try:
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
            finally:
                report.cleanup()


def test_create_bundle_report_v1():
    try:
        report = BundleAnalysisReport()
        session_id, bundle_name = report.ingest(sample_bundle_stats_path_4)
        assert session_id == 1
        assert bundle_name == "sample"

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
        session_id, bundle_name = bundle_analysis_report.ingest(
            sample_bundle_stats_path
        )
        assert session_id == 1
        assert bundle_name == "sample"

        session_id, bundle_name = bundle_analysis_report.ingest(
            sample_bundle_stats_path_5
        )
        assert session_id == 2
        assert bundle_name == "sample2"

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
        with get_db_session(bundle_analysis_report.db_path) as db_session:
            session_id, bundle_name = bundle_analysis_report.ingest(
                sample_bundle_stats_path
            )
            assert session_id == 1
            assert bundle_name == "sample"

            session_id, bundle_name = bundle_analysis_report.ingest(
                sample_bundle_stats_path_5
            )
            assert session_id == 2
            assert bundle_name == "sample2"

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


def test_create_bundle_report_without_and_with_compare_sha():
    try:
        report = BundleAnalysisReport()
        with get_db_session(report.db_path) as db_session:
            session_id, bundle_name = report.ingest(sample_bundle_stats_path)
            assert session_id == 1
            assert bundle_name == "sample"

            res = db_session.query(Metadata).filter_by(key="compare_sha").all()
            assert len(res) == 0

            session_id, bundle_name = report.ingest(
                sample_bundle_stats_path, "compare_sha_123"
            )
            assert session_id == 2
            assert bundle_name == "sample"

            res = db_session.query(Metadata).filter_by(key="compare_sha").all()
            assert len(res) == 1
            assert res[0].value == "compare_sha_123"
    finally:
        report.cleanup()


def test_bundle_report_asset_type_javascript():
    test_cases = [
        {
            "version": "v1",
            "path": "sample_bundle_stats_asset_type_javascript_v1.json",
            "expected_total_size": 90,
            "expected_js_size": 60,
        },
        {
            "version": "v2",
            "path": "sample_bundle_stats_asset_type_javascript_v2.json",
            "expected_total_size": 90,
            "expected_js_size": 60,
        },
    ]

    def load_and_test_report(
        version, report_path, expected_total_size, expected_js_size
    ):
        report = BundleAnalysisReport()
        try:
            report.ingest(report_path)
            bundle_report = report.bundle_report("sample")
            asset_reports = list(bundle_report.asset_reports())
            assert bundle_report.total_size() == expected_total_size, (
                f"Version {version}: Total size mismatch"
            )

            total_js_size = sum(
                asset.size
                for asset in asset_reports
                if asset.asset_type == AssetType.JAVASCRIPT
            )
            assert total_js_size == expected_js_size, (
                f"Version {version}: JS size mismatch"
            )
        finally:
            report.cleanup()

    for case in test_cases:
        report_path = Path(__file__).parent.parent.parent / "samples" / case["path"]
        load_and_test_report(
            case["version"],
            report_path,
            case["expected_total_size"],
            case["expected_js_size"],
        )


def test_bundle_report_total_gzip_size():
    try:
        report = BundleAnalysisReport()
        session_id, bundle_name = report.ingest(sample_bundle_stats_path)
        assert session_id == 1
        assert bundle_name == "sample"

        assert report.metadata() == {
            MetadataKey.SCHEMA_VERSION: SCHEMA_VERSION,
        }

        bundle_reports = list(report.bundle_reports())
        assert len(bundle_reports) == 1

        bundle_report = report.bundle_report("invalid")
        assert bundle_report is None
        bundle_report = report.bundle_report("sample")

        assert bundle_report.total_size() == 150572
        assert bundle_report.total_gzip_size() == 150567
    finally:
        report.cleanup()


def test_bundle_report_dynamic_imports_object_model():
    try:
        report = BundleAnalysisReport()
        with get_db_session(report.db_path) as db_session:
            # Check that the DB is set up correctly
            # 1 chunk has 2, another chunk has 1
            report.ingest(sample_bundle_stats_path_7)

            query = (
                select(Chunk.unique_external_id, Asset.name)
                .join(DynamicImport, Chunk.id == DynamicImport.chunk_id)
                .join(Asset, Asset.id == DynamicImport.asset_id)
                .order_by(Chunk.unique_external_id)
            )

            results = db_session.execute(query).all()

            result_dicts = [
                {"unique_external_id": unique_external_id, "asset_name": asset_name}
                for unique_external_id, asset_name in results
            ]

            assert result_dicts == [
                {
                    "asset_name": "index-C-Z8zsvD.js",
                    "unique_external_id": "1-LazyComponent",
                },
                {
                    "asset_name": "index-C-Z8zsvD.js",
                    "unique_external_id": "2-index",
                },
                {
                    "asset_name": "LazyComponent-BBSC53Nv.js",
                    "unique_external_id": "2-index",
                },
            ]

            # Check that the DB is set up correctly after a rewrite of a new file
            # 1 chunk has 1, another chunk has 1, another chunk has 1
            report.ingest(sample_bundle_stats_path_8)

            query = (
                select(Chunk.unique_external_id, Asset.name)
                .join(DynamicImport, Chunk.id == DynamicImport.chunk_id)
                .join(Asset, Asset.id == DynamicImport.asset_id)
                .order_by(Chunk.unique_external_id)
            )

            results = db_session.execute(query).all()

            result_dicts = [
                {"unique_external_id": unique_external_id, "asset_name": asset_name}
                for unique_external_id, asset_name in results
            ]

            assert result_dicts == [
                {
                    "asset_name": "LazyComponent-BBSC53Nv.js",
                    "unique_external_id": "0-index",
                },
                {
                    "asset_name": "index-C-Z8zsvD.js",
                    "unique_external_id": "1-LazyComponent",
                },
                {
                    "asset_name": "index-C-Z8zsvD.js",
                    "unique_external_id": "2-index",
                },
            ]

    finally:
        report.cleanup()


def test_bundle_report_dynamic_imports_fetching():
    try:
        report = BundleAnalysisReport()
        report.ingest(sample_bundle_stats_path_7)
        bundle_report = report.bundle_report("dynamic_imports")

        # There should only be 3 dynamic imports total
        dynamic_imports = []
        for asset in list(bundle_report.asset_reports()):
            dynamic_imports.extend(asset.dynamically_imported_assets())
        assert len(dynamic_imports) == 3

        # 1 of them should be from the asset called: LazyComponent-BBSC53Nv.js
        asset = bundle_report.asset_report_by_name("LazyComponent-BBSC53Nv.js")
        imports = [item for item in asset.dynamically_imported_assets()]
        assert len(imports) == 1
        assert imports[0].hashed_name == "index-C-Z8zsvD.js"

        # 2 of them should be from the asset called: assets/index-oTNkmlIs.js
        asset = bundle_report.asset_report_by_name("assets/index-oTNkmlIs.js")
        imports = [item.hashed_name for item in asset.dynamically_imported_assets()]
        assert len(imports) == 2
        assert "index-C-Z8zsvD.js" in imports
        assert "LazyComponent-BBSC53Nv.js" in imports
    finally:
        report.cleanup()


def test_bundle_report_routes():
    try:
        report = BundleAnalysisReport()
        report.ingest(sample_bundle_stats_path_6)
        bundle_report = report.bundle_report("sample")
        route_map = bundle_report.routes()

        # Total of 4 routes in this bundle
        assert len(route_map) == 4

        # "/" route has two Assets
        assets = sorted([item.hashed_name for item in route_map["/"]])
        assert assets == [
            "_app/immutable/nodes/0.CL_S-12h.js",
            "_app/immutable/nodes/2.BMQFqo-e.js",
        ]

        # "/about" has one asset
        assets = sorted([item.hashed_name for item in route_map["/about"]])
        assert assets == ["_app/immutable/nodes/3.BqQOub2U.js"]

        # "/sverdle" has one asset
        assets = sorted([item.hashed_name for item in route_map["/sverdle"]])
        assert assets == ["_app/immutable/nodes/4.CcjRtXvw.js"]

        # "/sverdle/how-to-play" has one asset
        assets = sorted(
            [item.hashed_name for item in route_map["/sverdle/how-to-play"]]
        )
        assert assets == ["_app/immutable/nodes/5.CwxmUzn6.js"]
    finally:
        report.cleanup()


def test_bundle_report_route_report_with_dynamic_imports():
    try:
        report = BundleAnalysisReport()
        report.ingest(sample_bundle_stats_path_9)
        bundle_report = report.bundle_report("dynamic_imports")

        route_report = bundle_report.full_route_report()

        assert route_report.get_sizes() == {
            "/sverdle/about": 2111,
            "/sverdle/careers": 2100,
            "/sverdle/faq": 2110,
            "/sverdle/users": 2111,
        }
        assert route_report.get_size("/sverdle/fake") is None
        assert route_report.get_size("/sverdle/about") == 2111
        assert route_report.get_size("/sverdle/careers") == 2100
        assert route_report.get_size("/sverdle/faq") == 2110
        assert route_report.get_size("/sverdle/users") == 2111
    finally:
        report.cleanup()


@pytest.mark.parametrize("version", ["1", "2", "3"])
def test_bundle_report_cleans_bad_chunks(version):
    try:
        report = BundleAnalysisReport()

        # Read and modify the JSON content
        with open(sample_bundle_stats_path_10, "r") as f:
            content = f.read().replace("__VERSION__", version)

        # Create a temporary file with the modified content
        import tempfile

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as temp:
            temp.write(content)
            temp_path = Path(temp.name)

        report.ingest(temp_path)
        bundle_report = report.bundle_report("sample")

        assets = sorted([item.hashed_name for item in bundle_report.asset_reports()])
        assert assets == [
            "assets/LazyComponent-fcbb0922.js",
        ]
        temp_path.unlink()
    finally:
        report.cleanup()
