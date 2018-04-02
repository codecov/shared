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


def test_get_slice():
    def filter_lines(line):
        if line.coverage == 3:
            return
        return line
    r = ReportFile(name='folder/file.py', lines=[ReportLine(1), ReportLine(2), ReportLine(3), ReportLine(4)], line_modifier=filter_lines)
    assert list(r[2:4]) == [(2, ReportLine(coverage=2, type=None, sessions=None, messages=None, complexity=None))]


@pytest.mark.parametrize('r, boolean', [
    (ReportFile(name='name.py'), False),
    (ReportFile(name='name.py', lines=[ReportLine(1)]), True),
])
def test_non_zero(r, boolean):
    assert bool(r) is boolean


def test_contains():
    r = ReportFile('file.py', lines=[ReportLine(1), ReportLine(2)])
    assert (2 in r) is True
    assert (7 in r) is False


def test_contains_exception():
    r = ReportFile('folder/file.py')
    with pytest.raises(Exception) as e_info:
        'str' in r
    assert e_info.value.message == "expecting type int got <type 'str'>"


def test_report_file_get():
    r = ReportFile(name='folder/file.py', lines=[ReportLine(), ReportLine()])
    assert r.get(1) == ReportLine()


def test_report_file_get_filter():
    r = ReportFile(name='folder/file.py', lines=[ReportLine(), ReportLine()], line_modifier=lambda l: l)
    assert r.get(1) == ReportLine()


def test_report_file_get_filter_none():
    r = ReportFile(name='folder/file.py', lines=[ReportLine(), ReportLine()], line_modifier=lambda l: None)
    assert r.get(1) is None


@pytest.mark.parametrize('get_val, error_message', [
    ('str', "expecting type int got <type 'str'>"),
    (-1, 'Line number must be greater then 0. Got -1'),
])
def test_report_file_get_exception(get_val, error_message):
    r = ReportFile('folder/file.py')
    with pytest.raises(Exception) as e_info:
        r.get(get_val)
    assert e_info.value.message == error_message


# TODO branch where this calls merge_line
@pytest.mark.parametrize('r, boolean, lines', [
    (ReportFile(name='folder/file.py', ignore={'eof':'N', 'lines':[1,10]}), False, []),
    (ReportFile(name='file.py'), True, [(1, ReportLine(1))]),
])
def test_append(r, boolean, lines):
    assert r.append(1, ReportLine(1)) is boolean
    assert list(r.lines) == lines


@pytest.mark.parametrize('key, val, error_message', [
    ('str', ReportLine(), "expecting type int got <type 'str'>"),
    (1, 'str', "expecting type ReportLine got <type 'str'>"),
    (-1, ReportLine(), 'Line number must be greater then 0. Got -1'),
])
def test_report_file_append_exception(key, val, error_message):
    r = ReportFile('folder/file.py')
    with pytest.raises(Exception) as e_info:
        r.append(key, val)
    assert e_info.value.message == error_message


# TODO branch where merge_line is called
@pytest.mark.parametrize('r, list_before, merge_val, merge_return, list_after', [
    (ReportFile(name='file.py'), [], None, None, []),
    (ReportFile(name='file.rb'), [], ReportFile(name='file.rb', lines=[ReportLine(2)]), True, [(1, ReportLine(2))]),
    (ReportFile(name='file.rb', totals=[1, 2, 3]), [], ReportFile(name='file.rb'), False, []),
])
def test_merge(r, list_before, merge_val, merge_return, list_after):
    assert list(r.lines) == list_before
    assert r.merge(merge_val) == merge_return
    assert list(r.lines) == list_after


def test_merge_exception():
    r = ReportFile(name='name.py')
    with pytest.raises(Exception) as e_info:
        r.merge('str')
    assert e_info.value.message == "expecting type ReportFile got <type 'str'>"


@pytest.mark.parametrize('r, totals', [
    (ReportFile(name='file.py', totals=[0]), ReportTotals(0)),
    (ReportFile(name='file.py', totals=[0], line_modifier=lambda l: l), ReportTotals(0, coverage=None)),
])
def test_totals(r, totals):
    assert r.totals == totals


@pytest.mark.parametrize('lines_before, line_modifier, lines_after', [
    ([(1, ReportLine(1)), (2, ReportLine(2))], None, [(1, ReportLine(1)), (2, ReportLine(2))]),
    ([(1, ReportLine(1)), (2, ReportLine(2))], lambda l: None, []),
])
def test_apply_line_modifier(lines_before, line_modifier, lines_after):
    r = ReportFile('files', lines=[ReportLine(1), ReportLine(2)])
    assert list(r.lines) == lines_before
    r.apply_line_modifier(line_modifier)
    assert list(r.lines) == lines_after


@pytest.mark.parametrize('r, lines', [
    (ReportFile(name='folder/file.py', lines=[ReportLine(1), ReportLine(0)], line_modifier=lambda l: None), []),
    (ReportFile(name='asd', lines=[[1]]), [(1, ReportLine(1))]),
])
def test_report_file_lines(r, lines):
    assert list(r.lines) == lines


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


@pytest.mark.parametrize('r, diff, new_file, boolean', [
    (ReportFile('file.py'), {
        'segments': []
    }, ReportFile('new.py'), False),
    (ReportFile('file.py'), {
        'segments': [
            {
                'header': [1, 1, 1, 1],
                'lines': ['- afefe', '+ fefe', '=']
            }
        ]
    }, ReportFile('new.py'), False),
    (ReportFile('file.py', lines=[ReportLine(1), ReportLine(2)]), {
        'segments': [
            {
                'header': [1, 1, 1, 1],
                'lines': ['- afefe', '+ fefe', '=']
            }
        ]
    }, ReportFile('new.py'), True),
    (ReportFile('file.py'), {
        'segments': [
            {
                'header': [1, 1, 1, 1],
                'lines': ['- afefe', '+ fefe', '=']
            }
        ]
    }, ReportFile('new.py', lines=[ReportLine(1), ReportLine(2)]), True),
])
def test_does_diff_adjust_tracked_lines(r, diff, new_file, boolean):
    assert r.does_diff_adjust_tracked_lines(diff, new_file) is boolean


def test_shift_lines_by_diff():
    r = ReportFile(name='folder/file.py', lines=[ReportLine(), ReportLine()])
    assert len(list(r.lines)) == 2
    r.shift_lines_by_diff({
        'segments': [
            {
                # [-, -, POS_to_start, new_lines_added]
                'header': [1, 1, 1, 1],
                'lines': ['- afefe', '+ fefe', '=']
            }
        ]
    })
    assert len(list(r.lines)) == 1


@pytest.mark.parametrize('r, encoded_val', [
    (ReportFile('name.py'), '{}\n'),
    (ReportFile('name.py', lines=[ReportLine(1), ReportLine(2)]), 'null\n[1]\n[2]'),
])
def test_encode(r, encoded_val):
    assert r._encode() == encoded_val


@pytest.mark.parametrize('r, lines_before, ignore_options, lines_after', [
    (ReportFile('file.py', lines=[ReportLine(0)]),
     [(1, ReportLine(0))],
     {},
     [(1, ReportLine(0))]),
    (ReportFile('file.py', lines=[ReportLine(0), ReportLine(1), ReportLine(2)]),
     [(1, ReportLine(0)), (2, ReportLine(1)), (3, ReportLine(2))],
     {'eof': 1},
     [(1, ReportLine(0))]),
    (ReportFile('file.py', lines=[ReportLine(0), ReportLine(1), ReportLine(2)]),
     [(1, ReportLine(0)), (2, ReportLine(1)), (3, ReportLine(2))],
     {'lines': [1, 2]},
     [(3, ReportLine(2))]),
])
def test_ignore_lines(r, lines_before, ignore_options, lines_after):
    assert list(r.lines) == lines_before
    r.ignore_lines(**ignore_options)
    assert list(r.lines) == lines_after
