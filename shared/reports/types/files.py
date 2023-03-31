from dataclasses import dataclass
from typing import Any

from shared.reports.types.totals import ReportTotals, SessionTotalsArray


@dataclass
class ReportFileSummary(object):
    file_index: int
    file_totals: ReportTotals = None
    session_totals: SessionTotalsArray = None
    diff_totals: Any = None

    def __init__(
        self,
        file_index,
        file_totals=None,
        session_totals=None,
        diff_totals=None,
        *args,
        **kwargs
    ) -> None:
        self.file_index = file_index
        self.file_totals = file_totals
        self.diff_totals = diff_totals
        self.session_totals = SessionTotalsArray.build_from_encoded_data(session_totals)

    def astuple(self):
        return (
            self.file_index,
            self.file_totals,
            self.session_totals,
            self.diff_totals,
        )


@dataclass
class NetworkFile(object):
    totals: ReportTotals
    session_totals: ReportTotals
    diff_totals: ReportTotals

    def astuple(self):
        return (
            self.totals.astuple(),
            [s.astuple() for s in self.session_totals] if self.session_totals else None,
            self.diff_totals.astuple() if self.diff_totals else None,
        )
