import pytest
from src.utils.tuples import ReportTotals
from src.utils.sessions import Session
from src.utils.ReportEncoder import ReportEncoder


@pytest.mark.parametrize('obj, res', [
    (ReportTotals(), []),
    (ReportTotals('files', 'lines'), ['files', 'lines']),
    (Session('id', 'totals'), {
        'N': None,
        'a': None,
        'c': None,
        'e': None,
        'd': None,
        'f': None,
        'j': None,
        'n': None,
        'p': None,
        'u': None,
        't': 'totals'
    }),
])
def test_report_encoder(obj, res):
    assert ReportEncoder().default(obj) == res


def test_exception_report_encoder():
    with pytest.raises(Exception) as e_info:
        ReportEncoder().default([1, 2])
    assert e_info.value.message == '[1, 2] is not JSON serializable'
