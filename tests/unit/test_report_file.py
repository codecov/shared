import pytest
from src.reports import ReportFile, ReportTotals, ReportLine


def test_report_file_constructor():
    r = ReportFile('folder/file.py', [0, 1, 1, 1], None, None, None, None)
    assert r.name == 'folder/file.py'


def test_repr():
    r = ReportFile('folder/file.py', [0, 1, 1, 1], None, None, None, None)
    assert repr(r) == '<ReportFile name=folder/file.py lines=0>'


def test_get_item():
    r = ReportFile('folder/file.py', [0, 1, 1, 1], None, None, None, None)
    assert r['totals'] == ReportTotals(0, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0)
    with pytest.raises(Exception) as e_info:
        r[[]]
    assert e_info.value.message == "expecting type int got <type 'list'>"
    with pytest.raises(Exception) as e_info:
        r[-1]
    assert e_info.value.message == 'Line number must be greater then 0. Got -1'


def test_set_item():
    r = ReportFile('folder/file.py')
    with pytest.raises(Exception) as e_info:
        r['str'] = 1
    assert e_info.value.message == "expecting type int got <type 'str'>"
    with pytest.raises(Exception) as e_info:
        r[1] = 'str'
    assert e_info.value.message == "expecting type ReportLine got <type 'str'>"
    with pytest.raises(Exception) as e_info:
        r[-1] = ReportLine()
    assert e_info.value.message == 'Line number must be greater then 0. Got -1'
