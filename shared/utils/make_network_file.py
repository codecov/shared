from shared.reports.types import NetworkFile, ReportTotals


def make_network_file(totals, diff=None):
    return NetworkFile(
        ReportTotals(*totals) if totals else ReportTotals(),
        ReportTotals(*diff) if diff else None,
    )
