import pytest
from src.utils.tuples import ReportTotals
from src.utils.sum_totals import sum_totals


@pytest.mark.unit
@pytest.mark.parametrize('totals, res', [
    ([ReportTotals(), ReportTotals(3, 3, 3, 3), ReportTotals()], ReportTotals(3, 3, 3, 3, 0, '100')),
    ([ReportTotals()], ReportTotals(1, 0, 0, 0, 0, '100')),
    ([], ReportTotals())
])
def test_sum_totals(totals, res):
    assert sum_totals(totals) == res
