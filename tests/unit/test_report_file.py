import pytest
from src.utils.tuples import ReportTotals, ReportLine
from src.ReportFile import ReportFile


def test_report_file_constructor():
    r1 = ReportFile('folder/file.py', [0, 1, 1, 1], None, None, None, None)
    assert r1.name == 'folder/file.py'
    r2 = ReportFile('file.py', lines='\nline@1\n\nline@3') # TODO what should be in lines because r2.lines not working
    # print r2.lines.next()
    assert r2.name == 'file.py'


def test_repr():
    r = ReportFile('folder/file.py', [0, 1, 1, 1], None, None, None, None)
    assert repr(r) == '<ReportFile name=folder/file.py lines=0>'


@pytest.mark.parametrize('r, get_val, res', [
    (ReportFile('folder/file.py', [0, 1, 1, 1], None, None, None, None), 'totals', ReportTotals(0, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0)),
    (ReportFile('file.py', lines=[ReportLine(), ReportLine()]), 1, ReportLine()),
])
def test_get_item(r, get_val, res):
    assert r[get_val] == res


@pytest.mark.parametrize('get_val, error_message', [
    ([], "expecting type int got <type 'list'>"),
    (-1, 'Line number must be greater then 0. Got -1'),
    (1, 'Line #1 not found in report'),
])
def test_get_item_exception(get_val, error_message):
    r = ReportFile('folder/file.py', [0, 1, 1, 1], None, None, None, None)
    with pytest.raises(Exception) as e_info:
        r[get_val]
    assert e_info.value.message == error_message


@pytest.mark.parametrize('r, get_val', [
    (ReportFile(name='folder/file.py', lines=[ReportLine(1)], ignore={'eof':'N', 'lines':[1,10]}), ReportLine(1)),
    (ReportFile(name='folder/file.py', lines=[ReportLine(1)]), ReportLine(0)),
])
def test_set_item(r, get_val):
    assert r[1] == ReportLine(1)
    r[1] = ReportLine(0)
    assert r[1] == get_val


@pytest.mark.parametrize('index, set_val, error_message', [
    ('str', 1, "expecting type int got <type 'str'>"),
    (1, 'str', "expecting type ReportLine got <type 'str'>"),
    (-1, ReportLine(), 'Line number must be greater then 0. Got -1'),
])
def test_set_item_exception(index, set_val, error_message):
    r = ReportFile('folder/file.py')
    with pytest.raises(Exception) as e_info:
        r[index] = set_val
    assert e_info.value.message == error_message


def test_len():
    r = ReportFile(name='folder/file.py', lines=[ReportLine(1), ReportLine(), None])
    assert len(r) == 2


def test_eol():
    r = ReportFile(name='folder/file.py', lines=[ReportLine(1), ReportLine(), None])
    assert r.eof == 4


def test_contains():
    r = ReportFile('folder/file.py')
    with pytest.raises(Exception) as e_info:
        'str' in r
    assert e_info.value.message == "expecting type int got <type 'str'>"
    boolean = 100 in r
    assert boolean is False


def test_report_file_get():
    r = ReportFile(name='folder/file.py', lines=[ReportLine(), ReportLine()])
    assert r.get(1) == ReportLine()


def test_report_file_get_filter():
    def filter_lines(line):
        return line
    r = ReportFile(name='folder/file.py', lines=[ReportLine(), ReportLine()], line_modifier=filter_lines)
    assert r.get(1) == ReportLine()


def test_report_file_get_filter_none():
    def filter_lines(line):
        return
    r = ReportFile(name='folder/file.py', lines=[ReportLine(), ReportLine()], line_modifier=filter_lines)
    assert r.get(1) is None


def test_report_file_get_exception():
    r = ReportFile('folder/file.py')
    with pytest.raises(Exception) as e_info:
        r.get('str')
    assert e_info.value.message == "expecting type int got <type 'str'>"
    with pytest.raises(Exception) as e_info:
        r.get(-1)
    assert e_info.value.message == 'Line number must be greater then 0. Got -1'


# TODO: unit test for append (mock the merge)


def test_report_file_append_exception():
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


def test_report_file_lines():
    def filter_lines(line):
        if line.coverage == 0:
            return
        return line
    r1 = ReportFile(name='folder/file.py', lines=[ReportLine(coverage=1), ReportLine(coverage=0)], line_modifier=filter_lines)
    assert list(r1.lines) == [(1, ReportLine(coverage=1))]
    r2 = ReportFile(name='asd', lines=[[1]])
    assert list(r2.lines) == [(1, ReportLine(coverage=1))]


def test_report_iter():
    def filter_lines(line):
        if line.coverage == 0:
            return
        return line
    r = ReportFile(name='folder/file.py', lines=[ReportLine(coverage=1), ReportLine(coverage=0)], line_modifier=filter_lines)
    lines = []
    for ln in r:
        lines.append(ln)
    assert lines == [ReportLine(coverage=1), None, None]  # TODO why extra None?
