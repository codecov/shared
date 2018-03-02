import pytest
from src.utils.tuples import ReportTotals
from src.utils.agg_totals import agg_totals


@pytest.mark.parametrize('totals, res', [
    ([None, xrange(6), xrange(6)], [2, 2, 4, 6, 8, '200.00000']),
    ([None, ReportTotals(*range(6)), ReportTotals(*range(6))], [2, 2, 4, 6, 8, '200.00000', 0, 0, 0, 0, 0, 0, 0]),
    ([], list((0,) * 13)),
    ('', [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]),

])
def test_agg_totals(totals, res):
    assert agg_totals(totals) == res
