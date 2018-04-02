import pytest
from mock import patch, PropertyMock
from src.utils.tuples import ReportLine, ReportTotals
from src.ReportFile import ReportFile, _ignore_to_func


def test_eof():
    with patch.object(ReportFile, '__init__', lambda self: None):
        r = ReportFile()
        type(r)._lines = PropertyMock(return_value=[ReportLine(1), ReportLine(2)])
        assert r.eof == 3


def test_len():
    with patch.object(ReportFile, '__init__', lambda self: None):
        r = ReportFile()
        type(r)._lines = PropertyMock(return_value=[ReportLine(1), ReportLine(2), None])
        assert len(r) == 2


def test_repr():
    with patch.object(ReportFile, '__init__', lambda self: None):
        r = ReportFile()
        type(r)._lines = PropertyMock(return_value=[ReportLine(1), ReportLine(2), None])
        type(r).name = PropertyMock(return_value='name.py')
        assert repr(r) == '<ReportFile name=name.py lines=2>'


@pytest.mark.parametrize('line_modifier, lines', [
    (None, [(1, ReportLine(1)), (2, ReportLine(2))]),
    (lambda line: None, [])
])
def test_lines(line_modifier, lines):
    with patch.object(ReportFile, '__init__', lambda self: None):
        r = ReportFile()
        type(r)._lines = PropertyMock(return_value=[ReportLine(1), ReportLine(2), None])
        type(r)._line_modifier = PropertyMock(return_value=line_modifier)
        assert list(r.lines) == lines


def test_iter():
    with patch.object(ReportFile, '__init__', lambda self: None):
        r = ReportFile()
        type(r)._lines = PropertyMock(return_value=[ReportLine(1), ReportLine(2), None])
        type(r)._line_modifier = PropertyMock(return_value=lambda line: line if line.coverage == 1 else None)
        lines = []
        for ln in r:
            lines.append(ln)
        assert lines == [ReportLine(1), None, None, None]


def test_get_item():
    with patch.object(ReportFile, '__init__', lambda self: None):
        r = ReportFile()
        type(r)._lines = PropertyMock(return_value=[ReportLine(1), ReportLine(2), ReportLine(3), ReportLine(4)])
        type(r)._totals = PropertyMock(return_value=ReportTotals(0, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0))
        assert r[1] == ReportLine(1)
        assert r['totals'] ==  ReportTotals(0, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0)


@pytest.mark.parametrize('get_val, error_message', [
    ([], "expecting type int got <type 'list'>"),
    (-1, 'Line number must be greater then 0. Got -1'),
    (1, 'Line #1 not found in report'),

])
def test_get_item_exception(get_val, error_message):
    with patch.object(ReportFile, '__init__', lambda self: None):
        r = ReportFile()
        type(r)._lines = PropertyMock(return_value=[])
        with pytest.raises(Exception) as e_info:
            r[get_val]
        assert e_info.value.message == error_message


@pytest.mark.parametrize('ignore, get_val', [
    ({'eof':'N', 'lines':[1,10]}, ReportLine(1)),
    ({}, ReportLine(0)),
])
def test_set_item(ignore, get_val):
    with patch.object(ReportFile, '__init__', lambda self: None):
        r = ReportFile()
        type(r)._lines = PropertyMock(return_value=[ReportLine(1)])
        type(r)._line_modifier = PropertyMock(return_value=None)
        type(r)._ignore = PropertyMock(return_value=_ignore_to_func(ignore))
        assert r[1] == ReportLine(1)
        r[1] = ReportLine(0)
        assert r[1] == get_val


@pytest.mark.parametrize('index, set_val, error_message', [
    ('str', 1, "expecting type int got <type 'str'>"),
    (1, 'str', "expecting type ReportLine got <type 'str'>"),
    (-1, ReportLine(), 'Line number must be greater then 0. Got -1'),
])
def test_set_item_exception(index, set_val, error_message):
    with patch.object(ReportFile, '__init__', lambda self: None):
        r = ReportFile()
        with pytest.raises(Exception) as e_info:
            r[index] = set_val
        assert e_info.value.message == error_message


def test_get_slice():
    with patch.object(ReportFile, '__init__', lambda self: None):
        r = ReportFile()
        type(r)._lines = PropertyMock(return_value=[ReportLine(1), ReportLine(2), ReportLine(3), ReportLine(4)])
        type(r)._line_modifier = PropertyMock(return_value=lambda line: None if line.coverage == 3 else line)
        assert list(r[2:4]) == [(2, ReportLine(coverage=2, type=None, sessions=None, messages=None, complexity=None))]


def test_contains():
    with patch.object(ReportFile, '__init__', lambda self: None):
        r = ReportFile()
        type(r)._lines = PropertyMock(return_value=[ReportLine(1), ReportLine(2), ReportLine(3), ReportLine(4)])
        assert (1 in r) is True
        assert (10 in r) is False


def test_contains_exception():
    with patch.object(ReportFile, '__init__', lambda self: None):
        r = ReportFile()
        with pytest.raises(Exception) as e_info:
            'str' in r
        assert e_info.value.message == "expecting type int got <type 'str'>"


@pytest.mark.parametrize('totals, boolean', [
    (ReportTotals(), False),
    (ReportTotals(1, 1, 1, 1), True),
])
def test_non_zero(totals, boolean):
    with patch.object(ReportFile, '__init__', lambda self: None):
        r = ReportFile()
        type(r)._totals = PropertyMock(return_value=totals)
        assert bool(r) is boolean


@pytest.mark.parametrize('line_modifier, line', [
    (None, ReportLine(1)),
    (lambda line: None, None),
])
def test_get(line_modifier, line):
    with patch.object(ReportFile, '__init__', lambda self: None):
        r = ReportFile()
        type(r)._lines = PropertyMock(return_value=[ReportLine(1), ReportLine(2), ReportLine(3), ReportLine(4)])
        type(r)._line_modifier = PropertyMock(return_value=line_modifier)
        assert r.get(1) == line


@pytest.mark.parametrize('get_val, error_message', [
    ('str', "expecting type int got <type 'str'>"),
    (-1, 'Line number must be greater then 0. Got -1'),
])
def test_report_file_get_exception(get_val, error_message):
    with patch.object(ReportFile, '__init__', lambda self: None):
        r = ReportFile()
        with pytest.raises(Exception) as e_info:
            r.get(get_val)
        assert e_info.value.message == error_message
