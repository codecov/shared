from covreports.reports.types import NetworkFile, ReportTotals


def make_network_file(totals, sessions=None, diff=None):
    return NetworkFile(
        ReportTotals(*totals) if totals else ReportTotals(),
        [ReportTotals(*session) if session else None for session in sessions]
        if sessions
        else None,
        ReportTotals(*diff) if diff else None,
    )
