from pathlib import Path

import pytest

from shared.bundle_analysis import (
    AssetChange,
    BundleAnalysisComparison,
    BundleAnalysisReport,
    BundleAnalysisReportLoader,
    BundleChange,
    MissingBaseReportError,
    MissingBundleError,
    MissingHeadReportError,
    RouteChange,
)
from shared.bundle_analysis.models import Bundle, get_db_session
from shared.storage.memory import MemoryStorageService

here = Path(__file__)
base_report_bundle_stats_path = (
    here.parent.parent.parent / "samples" / "sample_bundle_stats.json"
)
head_report_bundle_stats_path = (
    here.parent.parent.parent / "samples" / "sample_bundle_stats_other.json"
)
head_report_bundle_stats_path_route_base_1 = (
    here.parent.parent.parent
    / "samples"
    / "sample_bundle_stats_v3_comparison_base_1.json"
)
head_report_bundle_stats_path_route_base_2 = (
    here.parent.parent.parent
    / "samples"
    / "sample_bundle_stats_v3_comparison_base_2.json"
)
head_report_bundle_stats_path_route_head_1 = (
    here.parent.parent.parent
    / "samples"
    / "sample_bundle_stats_v3_comparison_head_1.json"
)
head_report_bundle_stats_path_route_head_2 = (
    here.parent.parent.parent
    / "samples"
    / "sample_bundle_stats_v3_comparison_head_2.json"
)


def test_bundle_analysis_comparison():
    loader = BundleAnalysisReportLoader(
        storage_service=MemoryStorageService({}),
        repo_key="testing",
    )

    comparison = BundleAnalysisComparison(
        loader=loader,
        base_report_key="base-report",
        head_report_key="head-report",
    )

    # raises errors when either report doesn't exist in storage
    with pytest.raises(MissingBaseReportError):
        comparison.base_report
    with pytest.raises(MissingHeadReportError):
        comparison.head_report

    try:
        base_report = BundleAnalysisReport()
        base_report.ingest(base_report_bundle_stats_path)

        old_bundle = Bundle(name="old")
        with get_db_session(base_report.db_path) as db_session:
            db_session.add(old_bundle)
            db_session.commit()

        head_report = BundleAnalysisReport()
        head_report.ingest(head_report_bundle_stats_path)

        new_bundle = Bundle(name="new")
        with get_db_session(head_report.db_path) as db_session:
            db_session.add(new_bundle)
            db_session.commit()

        loader.save(base_report, "base-report")
        loader.save(head_report, "head-report")
    finally:
        base_report.cleanup()
        head_report.cleanup()

    bundle_changes = comparison.bundle_changes()
    assert set(bundle_changes) == set(
        [
            BundleChange(
                bundle_name="sample",
                change_type=BundleChange.ChangeType.CHANGED,
                size_delta=1100,
                percentage_delta=0.73,
            ),
            BundleChange(
                bundle_name="new",
                change_type=BundleChange.ChangeType.ADDED,
                size_delta=0,
                percentage_delta=100,
            ),
            BundleChange(
                bundle_name="old",
                change_type=BundleChange.ChangeType.REMOVED,
                size_delta=0,
                percentage_delta=-100,
            ),
        ]
    )

    bundle_comparison = comparison.bundle_comparison("sample")
    asset_changes = bundle_comparison.asset_changes()
    assert set(asset_changes) == set(
        [
            AssetChange(
                asset_name="assets/other-*.svg",
                change_type=AssetChange.ChangeType.ADDED,
                size_delta=5126,
            ),
            AssetChange(
                asset_name="assets/index-*.css",
                change_type=AssetChange.ChangeType.CHANGED,
                size_delta=0,
            ),
            AssetChange(
                asset_name="assets/LazyComponent-*.js",
                change_type=AssetChange.ChangeType.CHANGED,
                size_delta=0,
            ),
            AssetChange(
                asset_name="assets/index-*.js",
                change_type=AssetChange.ChangeType.CHANGED,
                size_delta=100,
            ),
            AssetChange(
                asset_name="assets/index-*.js",
                change_type=AssetChange.ChangeType.CHANGED,
                size_delta=0,
            ),
            AssetChange(
                asset_name="assets/react-*.svg",
                change_type=AssetChange.ChangeType.REMOVED,
                size_delta=-4126,
            ),
        ]
    )

    total_size_delta = bundle_comparison.total_size_delta()
    assert total_size_delta == 1100
    assert total_size_delta == sum([change.size_delta for change in asset_changes])
    assert comparison.percentage_delta == 0.73

    with pytest.raises(MissingBundleError):
        comparison.bundle_comparison("new")


def test_bundle_analysis_total_size_delta():
    try:
        loader = BundleAnalysisReportLoader(
            storage_service=MemoryStorageService({}),
            repo_key="testing",
        )

        comparison = BundleAnalysisComparison(
            loader=loader,
            base_report_key="base-report",
            head_report_key="head-report",
        )

        base_report = BundleAnalysisReport()
        base_report.ingest(base_report_bundle_stats_path)

        old_bundle = Bundle(name="old")
        with get_db_session(base_report.db_path) as db_session:
            db_session.add(old_bundle)
            db_session.commit()

        head_report = BundleAnalysisReport()
        head_report.ingest(head_report_bundle_stats_path)

        new_bundle = Bundle(name="new")
        with get_db_session(head_report.db_path) as db_session:
            db_session.add(new_bundle)
            db_session.commit()

        loader.save(base_report, "base-report")
        loader.save(head_report, "head-report")

        assert comparison.total_size_delta == 1100
        assert comparison.percentage_delta == 0.73

    finally:
        base_report.cleanup()
        head_report.cleanup()


def test_bundle_analysis_route_comparison_by_bundle_name():
    loader = BundleAnalysisReportLoader(
        storage_service=MemoryStorageService({}),
        repo_key="testing",
    )

    comparison = BundleAnalysisComparison(
        loader=loader,
        base_report_key="base-report",
        head_report_key="head-report",
    )

    # raises errors when either report doesn't exist in storage
    with pytest.raises(MissingBaseReportError):
        comparison.base_report
    with pytest.raises(MissingHeadReportError):
        comparison.head_report

    try:
        base_report = BundleAnalysisReport()
        base_report.ingest(head_report_bundle_stats_path_route_base_1)
        base_report.ingest(head_report_bundle_stats_path_route_base_2)

        head_report = BundleAnalysisReport()
        head_report.ingest(head_report_bundle_stats_path_route_head_1)
        head_report.ingest(head_report_bundle_stats_path_route_head_2)

        loader.save(base_report, "base-report")
        loader.save(head_report, "head-report")
    finally:
        base_report.cleanup()
        head_report.cleanup()

    route_changes = comparison.bundle_routes_changes_by_bundle("bundle1")
    sorted_route_changes = sorted(route_changes, key=lambda x: x.route_name)
    expected_changes = [
        RouteChange(
            route_name="/sverdle/about",
            change_type=AssetChange.ChangeType.CHANGED,
            size_delta=900,
            percentage_delta=810.81,
        ),
        RouteChange(
            route_name="/sverdle/faq",
            change_type=AssetChange.ChangeType.REMOVED,
            size_delta=-110,
            percentage_delta=-100.0,
        ),
        RouteChange(
            route_name="/sverdle/faq-prime",
            change_type=AssetChange.ChangeType.ADDED,
            size_delta=1010,
            percentage_delta=100,
        ),
        RouteChange(
            route_name="/sverdle/users",
            change_type=AssetChange.ChangeType.CHANGED,
            size_delta=900,
            percentage_delta=810.81,
        ),
    ]

    assert sorted_route_changes == expected_changes


def test_bundle_analysis_route_comparison_all_bundles():
    loader = BundleAnalysisReportLoader(
        storage_service=MemoryStorageService({}),
        repo_key="testing",
    )

    comparison = BundleAnalysisComparison(
        loader=loader,
        base_report_key="base-report",
        head_report_key="head-report",
    )

    # raises errors when either report doesn't exist in storage
    with pytest.raises(MissingBaseReportError):
        comparison.base_report
    with pytest.raises(MissingHeadReportError):
        comparison.head_report

    try:
        base_report = BundleAnalysisReport()
        base_report.ingest(head_report_bundle_stats_path_route_base_1)
        base_report.ingest(head_report_bundle_stats_path_route_base_2)

        head_report = BundleAnalysisReport()
        head_report.ingest(head_report_bundle_stats_path_route_head_1)
        head_report.ingest(head_report_bundle_stats_path_route_head_2)

        loader.save(base_report, "base-report")
        loader.save(head_report, "head-report")
    finally:
        base_report.cleanup()
        head_report.cleanup()

    route_changes = comparison.bundle_routes_changes()

    assert len(route_changes) == 2
    assert "bundle1" in route_changes and "bundle2" in route_changes

    sorted_route_changes = sorted(route_changes["bundle1"], key=lambda x: x.route_name)
    expected_bundle1_changes = [
        RouteChange(
            route_name="/sverdle/about",
            change_type=AssetChange.ChangeType.CHANGED,
            size_delta=900,
            percentage_delta=810.81,
        ),
        RouteChange(
            route_name="/sverdle/faq",
            change_type=AssetChange.ChangeType.REMOVED,
            size_delta=-110,
            percentage_delta=-100.0,
        ),
        RouteChange(
            route_name="/sverdle/faq-prime",
            change_type=AssetChange.ChangeType.ADDED,
            size_delta=1010,
            percentage_delta=100,
        ),
        RouteChange(
            route_name="/sverdle/users",
            change_type=AssetChange.ChangeType.CHANGED,
            size_delta=900,
            percentage_delta=810.81,
        ),
    ]
    assert sorted_route_changes == expected_bundle1_changes

    sorted_route_changes = sorted(route_changes["bundle2"], key=lambda x: x.route_name)
    expected_bundle2_changes = [
        RouteChange(
            route_name="/sverdle/about",
            change_type=AssetChange.ChangeType.CHANGED,
            size_delta=9999,
            percentage_delta=9008.11,
        ),
        RouteChange(
            route_name="/sverdle/faq",
            change_type=AssetChange.ChangeType.REMOVED,
            size_delta=-110,
            percentage_delta=-100.0,
        ),
        RouteChange(
            route_name="/sverdle/faq-prime",
            change_type=AssetChange.ChangeType.ADDED,
            size_delta=10100,
            percentage_delta=100,
        ),
        RouteChange(
            route_name="/sverdle/users",
            change_type=AssetChange.ChangeType.CHANGED,
            size_delta=9999,
            percentage_delta=9008.11,
        ),
    ]
    assert sorted_route_changes == expected_bundle2_changes


def test_bundle_analysis_route_comparison_by_bundle_name_not_exist():
    loader = BundleAnalysisReportLoader(
        storage_service=MemoryStorageService({}),
        repo_key="testing",
    )

    comparison = BundleAnalysisComparison(
        loader=loader,
        base_report_key="base-report",
        head_report_key="head-report",
    )

    # raises errors when either report doesn't exist in storage
    with pytest.raises(MissingBaseReportError):
        comparison.base_report
    with pytest.raises(MissingHeadReportError):
        comparison.head_report

    try:
        base_report = BundleAnalysisReport()
        base_report.ingest(head_report_bundle_stats_path_route_base_1)

        head_report = BundleAnalysisReport()
        head_report.ingest(head_report_bundle_stats_path_route_head_1)

        loader.save(base_report, "base-report")
        loader.save(head_report, "head-report")
    finally:
        base_report.cleanup()
        head_report.cleanup()

    with pytest.raises(MissingBundleError):
        comparison.bundle_routes_changes_by_bundle("bundle2")
