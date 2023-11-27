from pathlib import Path

import pytest

from shared.bundle_analysis import (
    BundleAnalysisComparison,
    BundleChange,
    BundleReport,
    BundleReportLoader,
    MissingBaseReportError,
    MissingHeadReportError,
)
from shared.storage.memory import MemoryStorageService

here = Path(__file__)
base_report_bundle_stats_path = (
    here.parent.parent.parent / "samples" / "sample_bundle_stats.json"
)
head_report_bundle_stats_path = (
    here.parent.parent.parent / "samples" / "sample_bundle_stats_other.json"
)


def test_bundle_analysis_comparison():
    loader = BundleReportLoader(
        storage_service=MemoryStorageService({}),
        repo_key="testing",
    )

    comparison = BundleAnalysisComparison(
        loader=loader,
        base_sha="base-report",
        head_sha="head-report",
    )

    # raises errors when either report doesn't exist in storage
    with pytest.raises(MissingBaseReportError):
        comparison.base_report
    with pytest.raises(MissingHeadReportError):
        comparison.head_report

    base_report = BundleReport()
    base_report.ingest(base_report_bundle_stats_path)

    head_report = BundleReport()
    head_report.ingest(head_report_bundle_stats_path)

    loader.save(base_report, "base-report")
    loader.save(head_report, "head-report")

    changes = comparison.bundle_changes()
    assert changes == [
        BundleChange(
            bundle_id="assets/testing.svg",
            change_type=BundleChange.ChangeType.ADDED,
            size_delta=4126,
        ),
        BundleChange(
            bundle_id="assets/index.css",
            change_type=BundleChange.ChangeType.CHANGED,
            size_delta=-100,
        ),
        BundleChange(
            bundle_id="assets/other.js",
            change_type=BundleChange.ChangeType.ADDED,
            size_delta=1234,
        ),
        BundleChange(
            bundle_id="assets/index.js",
            change_type=BundleChange.ChangeType.CHANGED,
            size_delta=1000,
        ),
        BundleChange(
            bundle_id="assets/react.svg",
            change_type=BundleChange.ChangeType.REMOVED,
            size_delta=-4126,
        ),
        BundleChange(
            bundle_id="assets/LazyComponent.js",
            change_type=BundleChange.ChangeType.REMOVED,
            size_delta=-183,
        ),
    ]

    total_size_delta = comparison.total_size_delta()
    assert total_size_delta == 1951
    assert total_size_delta == sum([change.size_delta for change in changes])
