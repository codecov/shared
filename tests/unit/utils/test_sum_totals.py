import pytest

from shared.reports.types import ReportTotals
from shared.utils.totals import agg_totals, sum_totals


@pytest.mark.unit
@pytest.mark.parametrize(
    "totals, res",
    [
        (
            [ReportTotals(), ReportTotals(3, 3, 3, 3), ReportTotals()],
            ReportTotals(3, 3, 3, 3, 0, "100"),
        ),
        ([ReportTotals()], ReportTotals(1, 0, 0, 0, 0, coverage=None)),
        ([], ReportTotals(coverage=None)),
    ],
)
def test_sum_totals(totals, res):
    assert sum_totals(totals) == res


def test_agg_totals():
    total_list = [(1, 2, 3), (0, 0, 4), (0, 100, 12, 100000)]
    assert agg_totals(total_list) == ReportTotals(
        files=3,
        lines=102,
        hits=19,
        misses=0,
        partials=0,
        coverage="18.62745",
        branches=0,
        methods=0,
        messages=0,
        sessions=0,
        complexity=0,
        complexity_total=0,
        diff=0,
    )
