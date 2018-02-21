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


def test_contains():
    r = ReportFile('folder/file.py')
    with pytest.raises(Exception) as e_info:
        'str' in r
    assert e_info.value.message == "expecting type int got <type 'str'>"
    boolean = 100 in r
    assert boolean is False


def test_report_file_get_errors():
    r = ReportFile('folder/file.py')
    with pytest.raises(Exception) as e_info:
        r.get('str')
    assert e_info.value.message == "expecting type int got <type 'str'>"
    with pytest.raises(Exception) as e_info:
        r.get(-1)
    assert e_info.value.message == 'Line number must be greater then 0. Got -1'


def test_report_file_get_filter():
    def filter_lines(line):
        return None
    r = ReportFile(name='folder/file.py', lines=[ReportLine(), ReportLine()], line_modifier=filter_lines)
    assert r.get(1) is None


def test_report_file_errors():
    r = ReportFile('folder/file.py')
    with pytest.raises(Exception) as e_info:
        r.append('str', ReportLine())
    assert e_info.value.message == "expecting type int got <type 'str'>"
    with pytest.raises(Exception) as e_info:
        r.append(1, 'str')
    assert e_info.value.message == "expecting type ReportLine got <type 'str'>"
    with pytest.raises(Exception) as e_info:
        r.append(-1, ReportLine())
    assert e_info.value.message == 'Line number must be greater then 0. Got -1'
