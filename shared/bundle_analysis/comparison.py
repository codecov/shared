from dataclasses import dataclass
from enum import Enum
from functools import cached_property
from typing import List

from .report import BundleReport
from .storage import BundleReportLoader


class MissingBaseReportError(Exception):
    pass


class MissingHeadReportError(Exception):
    pass


@dataclass(frozen=True)
class BundleChange:
    """
    Info about how a bundle has changed between two different commits.
    """

    class ChangeType(Enum):
        ADDED = "added"
        REMOVED = "removed"
        CHANGED = "changed"

    bundle_id: str
    change_type: ChangeType
    size_delta: int


class BundleAnalysisComparison:
    """
    Compares bundle reports on two different commits.
    """

    def __init__(self, loader: BundleReportLoader, base_sha: str, head_sha: str):
        self.loader = loader
        self.base_sha = base_sha
        self.head_sha = head_sha

    @cached_property
    def base_report(self) -> BundleReport:
        base_report = self.loader.load(self.base_sha)
        if base_report is None:
            raise MissingBaseReportError()
        return base_report

    @cached_property
    def head_report(self) -> BundleReport:
        head_report = self.loader.load(self.head_sha)
        if head_report is None:
            raise MissingHeadReportError()
        return head_report

    def total_size_delta(self) -> int:
        base_size = self.base_report.total_size()
        head_size = self.head_report.total_size()
        return head_size - base_size

    def bundle_changes(self) -> List[BundleChange]:
        base_bundles = {bundle.id: bundle for bundle in self.base_report.bundles()}
        head_bundles = {bundle.id: bundle for bundle in self.head_report.bundles()}

        changes = []
        for bundle_id, bundle in head_bundles.items():
            if bundle_id not in base_bundles:
                change = BundleChange(
                    bundle_id=bundle_id,
                    change_type=BundleChange.ChangeType.ADDED,
                    size_delta=bundle.size,
                )
            else:
                prev_bundle = base_bundles[bundle_id]
                change = BundleChange(
                    bundle_id=bundle_id,
                    change_type=BundleChange.ChangeType.CHANGED,
                    size_delta=bundle.size - prev_bundle.size,
                )
            changes.append(change)

        for bundle_id, bundle in base_bundles.items():
            if bundle_id not in head_bundles:
                change = BundleChange(
                    bundle_id=bundle_id,
                    change_type=BundleChange.ChangeType.REMOVED,
                    size_delta=-bundle.size,
                )
                changes.append(change)

        return changes
