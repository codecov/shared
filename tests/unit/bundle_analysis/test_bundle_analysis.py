from pathlib import Path

from shared.bundle_analysis import BundleReport, BundleReportLoader
from shared.bundle_analysis.models import MetadataKey
from shared.storage.memory import MemoryStorageService

here = Path(__file__)
sample_bundle_stats_path = (
    here.parent.parent.parent / "samples" / "sample_bundle_stats.json"
)


def test_create_bundle_report():
    bundle_report = BundleReport()
    bundle_report.ingest(sample_bundle_stats_path)

    assert bundle_report.metadata() == {
        MetadataKey.SCHEMA_VERSION: 1,
    }

    bundles = list(bundle_report.bundles())
    assert len(bundles) == 4

    assert [(b.id, b.name, b.size, len(b.modules())) for b in bundles] == [
        ("assets/react.svg", "assets/react-35ef61ed.svg", 4126, 0),
        ("assets/index.css", "assets/index-d526a0c5.css", 1421, 0),
        ("assets/LazyComponent.js", "assets/LazyComponent-aa21a697.js", 183, 1),
        # FIXME: this is wrong since it's capturing the SVG and CSS modules as well.
        # Made a similar note in the parser code where the associations are made
        ("assets/index.js", "assets/index-8df741ec.js", 144469, 28),
    ]

    assert bundle_report.total_size() == 150199
    bundle_report.cleanup()


def test_save_load_bundle_report():
    bundle_report = BundleReport()
    bundle_report.ingest(sample_bundle_stats_path)

    loader = BundleReportLoader(
        storage_service=MemoryStorageService({}),
        repo_key="testing",
    )
    test_sha = "eeaedb769885e9547f517fa2c2eea41849663454"
    loader.save(bundle_report, test_sha)

    db_path = bundle_report.db_path
    bundle_report = loader.load(test_sha)

    initial_data = open(db_path, "rb").read()
    loaded_data = open(bundle_report.db_path, "rb").read()

    assert db_path != bundle_report.db_path
    assert len(initial_data) > 0
    assert initial_data == loaded_data

    bundle_report.cleanup()
