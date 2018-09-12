import pytest
from covreports.utils.tuples import ReportTotals
from covreports.utils.sessions import Session
from covreports.utils.ReportEncoder import ReportEncoder


@pytest.mark.unit
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


@pytest.mark.unit
def test_exception_report_encoder():
    with pytest.raises(Exception) as e_info:
        ReportEncoder().default([1, 2])
    assert str(e_info.value) == '[1, 2] is not JSON serializable'
