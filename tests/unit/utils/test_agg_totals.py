import pytest

from shared.reports.types import ReportTotals
from shared.utils.totals import agg_totals


@pytest.mark.unit
@pytest.mark.parametrize(
    "totals, res",
    [
        ([None, list(range(6)), list(range(6))], [2, 2, 4, 6, 8, "200.00000"]),
        (
            [None, ReportTotals(*list(range(6))), ReportTotals(*list(range(6)))],
            [2, 2, 4, 6, 8, "200.00000", 0, 0, 0, 0, 0, 0, 0],
        ),
        ([], ReportTotals(coverage=None)),
        ("", ReportTotals(coverage=None)),
        ([ReportTotals()], ReportTotals(files=1, coverage=None)),
        ([], ReportTotals(coverage=None)),
    ],
)
def test_agg_totals(totals, res):
    assert agg_totals(totals) == ReportTotals(*res)
