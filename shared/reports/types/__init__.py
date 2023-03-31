from dataclasses import dataclass

from shared.reports.types.files import NetworkFile, ReportFileSummary
from shared.reports.types.lines import CoverageDatapoint, LineSession, ReportLine
from shared.reports.types.totals import ReportTotals, SessionTotals, SessionTotalsArray


@dataclass
class Change(object):
    path: str = None
    new: bool = False
    deleted: bool = False
    in_diff: bool = None
    old_path: str = None
    totals: ReportTotals = None

    def __post_init__(self):
        if self.totals is not None:
            if not isinstance(self.totals, ReportTotals):
                self.totals = ReportTotals(*self.totals)


EMPTY = ""

TOTALS_MAP = tuple("fnhmpcbdMsCN")
