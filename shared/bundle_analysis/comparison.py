from collections import defaultdict
from dataclasses import dataclass
from enum import Enum
from functools import cached_property
from typing import List, MutableSet, Optional, Tuple

from shared.bundle_analysis.report import Bundle, BundleReport
from shared.bundle_analysis.storage import BundleReportLoader


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

    bundle_name: str
    change_type: ChangeType
    size_delta: int


BundleMatch = Tuple[Optional[Bundle], Optional[Bundle]]


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
        # this groups bundles by name
        # there can be multiple bundles with the same name and we
        # need to try and match them across base and head reports
        base_bundles = defaultdict(set)
        for bundle in self.base_report.bundles():
            base_bundles[bundle.name].add(bundle)
        head_bundles = defaultdict(set)
        for bundle in self.head_report.bundles():
            head_bundles[bundle.name].add(bundle)

        # match bundles across base and head
        # (A, B) means that bundle A transformed to bundle B
        # (X, None) means that bundle X was deleted
        # (None, X) means that bundle X was added
        matches: List[BundleMatch] = []
        bundle_names = []
        for bundle_name, bundles in head_bundles.items():
            bundle_names.append(bundle_name)
            matches += self._match_bundles(base_bundles[bundle_name], bundles)
        for bundle_name, bundles in base_bundles.items():
            if bundle_name not in bundle_names:
                matches += self._match_bundles(bundles, [])

        changes = []
        for (base_bundle, head_bundle) in matches:
            if base_bundle is None:
                change = BundleChange(
                    bundle_name=head_bundle.name,
                    change_type=BundleChange.ChangeType.ADDED,
                    size_delta=head_bundle.size,
                )
            elif head_bundle is None:
                change = BundleChange(
                    bundle_name=base_bundle.name,
                    change_type=BundleChange.ChangeType.REMOVED,
                    size_delta=-base_bundle.size,
                )
            else:
                change = BundleChange(
                    bundle_name=head_bundle.name,
                    change_type=BundleChange.ChangeType.CHANGED,
                    size_delta=head_bundle.size - base_bundle.size,
                )
            changes.append(change)

        return changes

    def _match_bundles(
        self, base_bundles: MutableSet[Bundle], head_bundles: MutableSet[Bundle]
    ) -> List[BundleMatch]:
        """
        The given base bundles and head bundles all have the same name.
        This method attempts to pick the most likely matching of bundles between
        base and head (so as to track their changes through time).

        The current approach is fairly naive and just picks the bundle with the
        closest size.  There are probably better ways of doing this that we can
        improve upon in the future.
        """
        n = max([len(base_bundles), len(head_bundles)])
        matches: List[BundleMatch] = []

        while len(matches) < n:
            if len(head_bundles) > 0:
                # we have an unmatched head bundle
                head_bundle = head_bundles.pop()

                if len(base_bundles) == 0:
                    # no more base bundles to match against
                    matches.append((None, head_bundle))
                else:
                    # try and find the most "similar" base bundle
                    size_deltas = {
                        abs(head_bundle.size - base_bundle.size): base_bundle
                        for base_bundle in base_bundles
                    }
                    min_delta = min(size_deltas.keys())
                    base_bundle = size_deltas[min_delta]

                    matches.append((base_bundle, head_bundle))
                    base_bundles.remove(base_bundle)
            elif len(base_bundles) > 0:
                # we have unmatched base bundles and no more head bundles
                base_bundle = base_bundles.pop()
                matches.append((base_bundle, None))
            else:
                # shouldn't ever get here
                raise Exception("incorrect bundle matching logic")  # pragma: no cover

        return matches
