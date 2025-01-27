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
    total_size_delta = bundle_comparison.total_size_delta()
    assert total_size_delta == 1100
    assert comparison.percentage_delta == 0.73

    with pytest.raises(MissingBundleError):
        comparison.bundle_comparison("new")


def test_bundle_asset_comparison_using_closest_size_delta():
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
    asset_comparisons = bundle_comparison.asset_comparisons()
    assert len(asset_comparisons) == 6

    asset_comparison_d = {}
    for asset_comparison in asset_comparisons:
        key = (
            asset_comparison.base_asset_report.hashed_name
            if asset_comparison.base_asset_report
            else None,
            asset_comparison.head_asset_report.hashed_name
            if asset_comparison.head_asset_report
            else None,
        )
        assert key not in asset_comparison_d
        asset_comparison_d[key] = asset_comparison

    # Check asset change is correct
    assert asset_comparison_d[
        ("assets/index-666d2e09.js", "assets/index-666d2e09.js")
    ].asset_change() == AssetChange(
        change_type=AssetChange.ChangeType.CHANGED,
        size_delta=0,
        asset_name="assets/index-*.js",
        percentage_delta=0,
        size_base=144577,
        size_head=144577,
    )
    assert asset_comparison_d[
        ("assets/index-c8676264.js", "assets/index-c8676264.js")
    ].asset_change() == AssetChange(
        change_type=AssetChange.ChangeType.CHANGED,
        size_delta=100,
        asset_name="assets/index-*.js",
        percentage_delta=64.94,
        size_base=154,
        size_head=254,
    )
    assert asset_comparison_d[
        (None, "assets/other-35ef61ed.svg")
    ].asset_change() == AssetChange(
        change_type=AssetChange.ChangeType.ADDED,
        size_delta=5126,
        asset_name="assets/other-*.svg",
        percentage_delta=100,
        size_base=0,
        size_head=5126,
    )
    assert asset_comparison_d[
        ("assets/index-d526a0c5.css", "assets/index-d526a0c5.css")
    ].asset_change() == AssetChange(
        change_type=AssetChange.ChangeType.CHANGED,
        size_delta=0,
        asset_name="assets/index-*.css",
        percentage_delta=0,
        size_base=1421,
        size_head=1421,
    )
    assert asset_comparison_d[
        ("assets/LazyComponent-fcbb0922.js", "assets/LazyComponent-fcbb0922.js")
    ].asset_change() == AssetChange(
        change_type=AssetChange.ChangeType.CHANGED,
        size_delta=0,
        asset_name="assets/LazyComponent-*.js",
        percentage_delta=0,
        size_base=294,
        size_head=294,
    )
    assert asset_comparison_d[
        ("assets/react-35ef61ed.svg", None)
    ].asset_change() == AssetChange(
        change_type=AssetChange.ChangeType.REMOVED,
        size_delta=-4126,
        asset_name="assets/react-*.svg",
        percentage_delta=-100,
        size_base=4126,
        size_head=0,
    )

    # Check asset contributing modules is correct
    module_reports = asset_comparison_d[
        ("assets/index-666d2e09.js", "assets/index-666d2e09.js")
    ].contributing_modules()
    assert [module.name for module in module_reports] == [
        "./vite/modulepreload-polyfill",
        "./commonjsHelpers.js",
        "../../node_modules/.pnpm/react@18.2.0/node_modules/react/jsx-runtime.js?commonjs-module",
        "../../node_modules/.pnpm/react@18.2.0/node_modules/react/cjs/react-jsx-runtime.production.min.js?commonjs-exports",
        "../../node_modules/.pnpm/react@18.2.0/node_modules/react/index.js?commonjs-module",
        "../../node_modules/.pnpm/react@18.2.0/node_modules/react/cjs/react.production.min.js?commonjs-exports",
        "../../node_modules/.pnpm/react@18.2.0/node_modules/react/cjs/react.production.min.js",
        "../../node_modules/.pnpm/react@18.2.0/node_modules/react/index.js",
        "../../node_modules/.pnpm/react@18.2.0/node_modules/react/cjs/react-jsx-runtime.production.min.js",
        "../../node_modules/.pnpm/react@18.2.0/node_modules/react/jsx-runtime.js",
        "../../node_modules/.pnpm/react-dom@18.2.0_react@18.2.0/node_modules/react-dom/client.js?commonjs-exports",
        "../../node_modules/.pnpm/react-dom@18.2.0_react@18.2.0/node_modules/react-dom/index.js?commonjs-module",
        "../../node_modules/.pnpm/react-dom@18.2.0_react@18.2.0/node_modules/react-dom/cjs/react-dom.production.min.js?commonjs-exports",
        "../../node_modules/.pnpm/scheduler@0.23.0/node_modules/scheduler/index.js?commonjs-module",
        "../../node_modules/.pnpm/scheduler@0.23.0/node_modules/scheduler/cjs/scheduler.production.min.js?commonjs-exports",
        "../../node_modules/.pnpm/scheduler@0.23.0/node_modules/scheduler/cjs/scheduler.production.min.js",
        "../../node_modules/.pnpm/scheduler@0.23.0/node_modules/scheduler/index.js",
        "../../node_modules/.pnpm/react-dom@18.2.0_react@18.2.0/node_modules/react-dom/cjs/react-dom.production.min.js",
        "../../node_modules/.pnpm/react-dom@18.2.0_react@18.2.0/node_modules/react-dom/index.js",
        "../../node_modules/.pnpm/react-dom@18.2.0_react@18.2.0/node_modules/react-dom/client.js",
        "./vite/preload-helper",
        "./src/assets/react.svg",
        "../../../../../../vite.svg",
        "./src/App.css",
        "./src/App.tsx",
        "./src/index.css",
        "./src/main.tsx",
        "./index.html",
    ]
    module_reports = asset_comparison_d[
        ("assets/index-c8676264.js", "assets/index-c8676264.js")
    ].contributing_modules()
    assert [module.name for module in module_reports] == [
        "./src/IndexedLazyComponent/IndexedLazyComponent.tsx",
        "./src/IndexedLazyComponent/index.ts",
        "./src/Other.tsx",
    ]
    module_reports = asset_comparison_d[
        (None, "assets/other-35ef61ed.svg")
    ].contributing_modules()
    assert [module.name for module in module_reports] == []
    module_reports = asset_comparison_d[
        ("assets/index-d526a0c5.css", "assets/index-d526a0c5.css")
    ].contributing_modules()
    assert [module.name for module in module_reports] == []
    module_reports = asset_comparison_d[
        ("assets/LazyComponent-fcbb0922.js", "assets/LazyComponent-fcbb0922.js")
    ].contributing_modules()
    assert [module.name for module in module_reports] == [
        "./src/LazyComponent/LazyComponent.tsx",
    ]
    module_reports = asset_comparison_d[
        ("assets/react-35ef61ed.svg", None)
    ].contributing_modules()
    assert [module.name for module in module_reports] == []

    # Check no contributing modules filter
    module_reports = asset_comparison_d[
        ("assets/index-666d2e09.js", "assets/index-666d2e09.js")
    ].contributing_modules()
    assert len(module_reports) == 28

    # Check no PR changed files
    module_reports = asset_comparison_d[
        ("assets/index-666d2e09.js", "assets/index-666d2e09.js")
    ].contributing_modules([])
    assert len(module_reports) == 0

    # Check with proper filtered files
    module_reports = asset_comparison_d[
        ("assets/index-666d2e09.js", "assets/index-666d2e09.js")
    ].contributing_modules(
        [
            "app1/index.html",
            "app2/index.html",  # <- don't match because dupe
            "./app1/src/main.tsx",
            "/example/svelte/app1/src/App.css",
            "abc/def/ghi.ts",  # <- don't match
        ]
    )
    assert set([module.name for module in module_reports]) == set(
        ["./index.html", "./src/App.css", "./src/main.tsx"]
    )


def test_bundle_asset_comparison_using_uuid():
    """
    In the default setup we have:
        (base:index-666d2e09.js, head:index-666d2e09.js): 144577 -> 144577
        (base:index-c8676264.js, head:index-c8676264.js): 154 -> 254
    this matches based on closes size delta, now we will update to the following UUIDs
        base:index-666d2e09.js -> UUID=123
        base:index-c8676264.js -> UUID=456
        head:index-666d2e09.js -> UUID=456
        head:index-c8676264.js -> UUID=123
    this will yield the following comparisons
        (base:index-666d2e09.js, head:index-c8676264.js): 144577 -> 254
        (base:index-c8676264.js, head:index-666d2e09.js): 154 -> 144577
    """
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

    # Update the UUIDs
    with get_db_session(comparison.base_report.db_path) as db_session:
        from shared.bundle_analysis.models import Asset

        db_session.query(Asset).filter(Asset.name == "assets/index-666d2e09.js").update(
            {Asset.uuid: "123"}, synchronize_session="fetch"
        )
        db_session.query(Asset).filter(Asset.name == "assets/index-c8676264.js").update(
            {Asset.uuid: "456"}, synchronize_session="fetch"
        )
        db_session.commit()

    with get_db_session(comparison.head_report.db_path) as db_session:
        from shared.bundle_analysis.models import Asset

        db_session.query(Asset).filter(Asset.name == "assets/index-666d2e09.js").update(
            {Asset.uuid: "456"}, synchronize_session="fetch"
        )
        db_session.query(Asset).filter(Asset.name == "assets/index-c8676264.js").update(
            {Asset.uuid: "123"}, synchronize_session="fetch"
        )
        db_session.commit()

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
    asset_comparisons = bundle_comparison.asset_comparisons()
    assert len(asset_comparisons) == 6

    asset_comparison_d = {}
    for asset_comparison in asset_comparisons:
        key = (
            asset_comparison.base_asset_report.hashed_name
            if asset_comparison.base_asset_report
            else None,
            asset_comparison.head_asset_report.hashed_name
            if asset_comparison.head_asset_report
            else None,
        )
        assert key not in asset_comparison_d
        asset_comparison_d[key] = asset_comparison

    # Check asset change is correct
    assert asset_comparison_d[
        ("assets/index-666d2e09.js", "assets/index-c8676264.js")
    ].asset_change() == AssetChange(
        change_type=AssetChange.ChangeType.CHANGED,
        size_delta=-144323,
        asset_name="assets/index-*.js",
        percentage_delta=-99.82,
        size_base=144577,
        size_head=254,
    )
    assert asset_comparison_d[
        ("assets/index-c8676264.js", "assets/index-666d2e09.js")
    ].asset_change() == AssetChange(
        change_type=AssetChange.ChangeType.CHANGED,
        size_delta=144423,
        asset_name="assets/index-*.js",
        percentage_delta=93781.17,
        size_base=154,
        size_head=144577,
    )
    assert asset_comparison_d[
        (None, "assets/other-35ef61ed.svg")
    ].asset_change() == AssetChange(
        change_type=AssetChange.ChangeType.ADDED,
        size_delta=5126,
        asset_name="assets/other-*.svg",
        percentage_delta=100,
        size_base=0,
        size_head=5126,
    )
    assert asset_comparison_d[
        ("assets/index-d526a0c5.css", "assets/index-d526a0c5.css")
    ].asset_change() == AssetChange(
        change_type=AssetChange.ChangeType.CHANGED,
        size_delta=0,
        asset_name="assets/index-*.css",
        percentage_delta=0,
        size_base=1421,
        size_head=1421,
    )
    assert asset_comparison_d[
        ("assets/LazyComponent-fcbb0922.js", "assets/LazyComponent-fcbb0922.js")
    ].asset_change() == AssetChange(
        change_type=AssetChange.ChangeType.CHANGED,
        size_delta=0,
        asset_name="assets/LazyComponent-*.js",
        percentage_delta=0,
        size_base=294,
        size_head=294,
    )
    assert asset_comparison_d[
        ("assets/react-35ef61ed.svg", None)
    ].asset_change() == AssetChange(
        change_type=AssetChange.ChangeType.REMOVED,
        size_delta=-4126,
        asset_name="assets/react-*.svg",
        percentage_delta=-100,
        size_base=4126,
        size_head=0,
    )


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
            size_base=111,
            size_head=1011,
        ),
        RouteChange(
            route_name="/sverdle/faq",
            change_type=AssetChange.ChangeType.REMOVED,
            size_delta=-110,
            percentage_delta=-100.0,
            size_base=110,
            size_head=0,
        ),
        RouteChange(
            route_name="/sverdle/faq-prime",
            change_type=AssetChange.ChangeType.ADDED,
            size_delta=1010,
            percentage_delta=100,
            size_base=0,
            size_head=1010,
        ),
        RouteChange(
            route_name="/sverdle/users",
            change_type=AssetChange.ChangeType.CHANGED,
            size_delta=900,
            percentage_delta=810.81,
            size_base=111,
            size_head=1011,
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
            size_base=111,
            size_head=1011,
        ),
        RouteChange(
            route_name="/sverdle/faq",
            change_type=AssetChange.ChangeType.REMOVED,
            size_delta=-110,
            percentage_delta=-100.0,
            size_base=110,
            size_head=0,
        ),
        RouteChange(
            route_name="/sverdle/faq-prime",
            change_type=AssetChange.ChangeType.ADDED,
            size_delta=1010,
            percentage_delta=100,
            size_base=0,
            size_head=1010,
        ),
        RouteChange(
            route_name="/sverdle/users",
            change_type=AssetChange.ChangeType.CHANGED,
            size_delta=900,
            percentage_delta=810.81,
            size_base=111,
            size_head=1011,
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
            size_base=111,
            size_head=10110,
        ),
        RouteChange(
            route_name="/sverdle/faq",
            change_type=AssetChange.ChangeType.REMOVED,
            size_delta=-110,
            percentage_delta=-100.0,
            size_base=110,
            size_head=0,
        ),
        RouteChange(
            route_name="/sverdle/faq-prime",
            change_type=AssetChange.ChangeType.ADDED,
            size_delta=10100,
            percentage_delta=100,
            size_base=0,
            size_head=10100,
        ),
        RouteChange(
            route_name="/sverdle/users",
            change_type=AssetChange.ChangeType.CHANGED,
            size_delta=9999,
            percentage_delta=9008.11,
            size_base=111,
            size_head=10110,
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


def test_bundle_analysis_route_comparison_different_bundle_names():
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
        head_report.ingest(head_report_bundle_stats_path_route_head_2)

        loader.save(base_report, "base-report")
        loader.save(head_report, "head-report")
    finally:
        base_report.cleanup()
        head_report.cleanup()

    route_changes = comparison.bundle_routes_changes()

    EXPECTED_CHANGES = {
        "bundle1": [
            RouteChange(
                change_type=RouteChange.ChangeType.REMOVED,
                size_delta=-111,
                route_name="/sverdle/about",
                percentage_delta=-100.0,
                size_base=111,
                size_head=0,
            ),
            RouteChange(
                change_type=RouteChange.ChangeType.REMOVED,
                size_delta=-110,
                route_name="/sverdle/faq",
                percentage_delta=-100.0,
                size_base=110,
                size_head=0,
            ),
            RouteChange(
                change_type=RouteChange.ChangeType.REMOVED,
                size_delta=-111,
                route_name="/sverdle/users",
                percentage_delta=-100.0,
                size_base=111,
                size_head=0,
            ),
        ],
        "bundle2": [
            RouteChange(
                change_type=RouteChange.ChangeType.ADDED,
                size_delta=10110,
                route_name="/sverdle/about",
                percentage_delta=100,
                size_base=0,
                size_head=10110,
            ),
            RouteChange(
                change_type=RouteChange.ChangeType.ADDED,
                size_delta=10100,
                route_name="/sverdle/faq-prime",
                percentage_delta=100,
                size_base=0,
                size_head=10100,
            ),
            RouteChange(
                change_type=RouteChange.ChangeType.ADDED,
                size_delta=10110,
                route_name="/sverdle/users",
                percentage_delta=100,
                size_base=0,
                size_head=10110,
            ),
        ],
    }

    assert len(route_changes) == 2
    assert (
        sorted(route_changes["bundle1"], key=lambda x: x.route_name)
        == EXPECTED_CHANGES["bundle1"]
    )
    assert (
        sorted(route_changes["bundle2"], key=lambda x: x.route_name)
        == EXPECTED_CHANGES["bundle2"]
    )
