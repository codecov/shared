from pathlib import Path
from typing import Dict

from shared.bundle_analysis import BundleAnalysisReport
from shared.bundle_analysis.models import Asset, AssetType

bundle_stats_prev_a_path = (
    Path(__file__).parent.parent.parent / "samples" / "asset_link_prev_a.json"
)

bundle_stats_prev_b_path = (
    Path(__file__).parent.parent.parent / "samples" / "asset_link_prev_b.json"
)

bundle_stats_curr_a_path = (
    Path(__file__).parent.parent.parent / "samples" / "asset_link_curr_a.json"
)

bundle_stats_curr_b_path = (
    Path(__file__).parent.parent.parent / "samples" / "asset_link_curr_b.json"
)


def _get_asset_mapping(
    bundle_analysis_report: BundleAnalysisReport, bundle_name: Asset
) -> Dict[str, str]:
    bundle_report = bundle_analysis_report.bundle_report(bundle_name)
    asset_report = list(bundle_report.asset_reports())
    return {asset.hashed_name: asset for asset in asset_report}


def test_asset_association():
    try:
        prev_bar = BundleAnalysisReport()
        prev_bar.ingest(bundle_stats_prev_a_path)
        prev_bar.ingest(bundle_stats_prev_b_path)

        prev_a_asset_mapping = _get_asset_mapping(prev_bar, "BundleA")
        prev_b_asset_mapping = _get_asset_mapping(prev_bar, "BundleB")

        curr_bar = BundleAnalysisReport()
        curr_bar.ingest(bundle_stats_curr_a_path)
        curr_bar.ingest(bundle_stats_curr_b_path)

        curr_a_asset_mapping_before = _get_asset_mapping(curr_bar, "BundleA")
        curr_b_asset_mapping_before = _get_asset_mapping(curr_bar, "BundleB")

        curr_bar.associate_previous_assets(prev_bar)

        curr_a_asset_mapping_after = _get_asset_mapping(curr_bar, "BundleA")
        curr_b_asset_mapping_after = _get_asset_mapping(curr_bar, "BundleB")

        # Check that non javscript asset types didn't have their UUIDs updated
        for hashed_name, asset in curr_a_asset_mapping_before.items():
            if asset.asset_type != AssetType.JAVASCRIPT:
                assert asset.uuid == curr_a_asset_mapping_after[hashed_name].uuid
        for hashed_name, asset in curr_b_asset_mapping_before.items():
            if asset.asset_type != AssetType.JAVASCRIPT:
                assert asset.uuid == curr_b_asset_mapping_after[hashed_name].uuid

        # Same name -> asset associated
        asset_a = prev_a_asset_mapping["asset-same-name-diff-modules.js"]
        assert (
            curr_a_asset_mapping_after["asset-same-name-diff-modules.js"].uuid
            == asset_a.uuid
        )
        asset_b = prev_b_asset_mapping["asset-same-name-diff-modules.js"]
        assert (
            curr_b_asset_mapping_after["asset-same-name-diff-modules.js"].uuid
            == asset_b.uuid
        )

        # Diff name, same modules -> asset associated
        asset_a = prev_a_asset_mapping["asset-diff-name-same-modules-ONE.js"]
        assert curr_a_asset_mapping_after["asset-diff-name-same-modules-TWO.js"]
        asset_b = prev_b_asset_mapping["asset-diff-name-same-modules-ONE.js"]
        assert curr_b_asset_mapping_after["asset-diff-name-same-modules-TWO.js"]

        # Diff name, diff modules -> asset not associated
        asset_a = prev_a_asset_mapping["asset-diff-name-diff-modules-ONE.js"]
        assert curr_a_asset_mapping_after["asset-diff-name-diff-modules-TWO.js"]
        asset_b = prev_b_asset_mapping["asset-diff-name-diff-modules-ONE.js"]
        assert curr_b_asset_mapping_after["asset-diff-name-diff-modules-TWO.js"]

    finally:
        prev_bar.cleanup()
        curr_bar.cleanup()
