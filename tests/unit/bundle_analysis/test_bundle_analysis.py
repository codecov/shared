from pathlib import Path

from shared.bundle_analysis import BundleAnalysisReport, BundleAnalysisReportLoader
from shared.bundle_analysis.models import MetadataKey
from shared.storage.memory import MemoryStorageService

sample_bundle_stats_path = (
    Path(__file__).parent.parent.parent / "samples" / "sample_bundle_stats.json"
)

sample_bundle_stats_path_2 = (
    Path(__file__).parent.parent.parent / "samples" / "sample_bundle_stats_other.json"
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
            (ar.name, ar.hashed_name, ar.size, len(ar.modules()))
            for ar in asset_reports
        ] == [
            ("assets/react-*.svg", "assets/react-35ef61ed.svg", 4126, 0),
            ("assets/index-*.css", "assets/index-d526a0c5.css", 1421, 0),
            ("assets/LazyComponent-*.js", "assets/LazyComponent-fcbb0922.js", 294, 1),
            ("assets/index-*.js", "assets/index-c8676264.js", 154, 2),
            # FIXME: this is wrong since it's capturing the SVG and CSS modules as well.
            # Made a similar note in the parser code where the associations are made
            ("assets/index-*.js", "assets/index-666d2e09.js", 144577, 28),
        ]

        assert bundle_report.total_size() == 150572
        assert report.session_count() == 1
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
