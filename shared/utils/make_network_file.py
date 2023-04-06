from shared.reports.types import NetworkFile, ReportTotals, SessionTotalsArray


def make_network_file(totals, sessions_totals: SessionTotalsArray = None, diff=None):
    return NetworkFile(
        ReportTotals(*totals) if totals else ReportTotals(),
        sessions_totals,
        ReportTotals(*diff) if diff else None,
    )
