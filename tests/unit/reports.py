import pytest
from json import dumps, loads
from mock import Mock
from src.reports import *


def json(d):
    return loads(dumps(d))


@pytest.mark.parametrize('_in, out', [
    ([(1, 2, 0), (4, 10, 1)], [[1, 2, 0], [4, 10, 1]]),  # outer == same
    ([[1, None, 1]], [[1, None, 1]]),  # single == same
    ([(2, 24, 1), (24, None, 0)], [[2, 24, 1], [24, None, 0]]),
    ([(2, 2, 1), (2, 2, 0)], None),
    ([(0, None, 28), (0, None, 0)], [[0, None, 28]]),
    ([(2, 35, 1), (35, None, 1)], [[2, None, 1]]),
    ([(2, 35, '1/2'), (35, None, '1/2')], [[2, None, '1/2']]),
    ([(2, 35, '1/2'), (35, None, '2/2')], [[2, 35, '1/2'], [35, None, '2/2']]),
    ([(None, 2, 1), (1, 5, 1)], [[0, 5, 1]]),
    ([(None, 1, 1), (1, 2, 0), (2, 3, 1)], [[1, 2, 0], [2, 3, 1]]),
    ([(1, None, 1), (2, None, 0)], [[1, None, 1]]),  # hit&miss overlay == hit
    ([(1, 5, 0), (4, 10, 1)], [[1, 4, 0], [4, 10, 1]]),  # intersect
    ([(1, 10, 0), (4, 6, 1)], [[1, 4, 0], [4, 6, 1], [6, 10, 0]]),  # inner overlay
])
def test_combine_partials(_in, out):
    assert combine_partials(_in) == out


@pytest.mark.parametrize('cov_list, res', [
    ([0], 0),
    ([0, 1], 1),
    ([0, '0/2', '1/2'], '1/2'),
    ([1, '0/2', '1/2'], '2/2'),
])
def test_merge_all(cov_list, res):
    assert merge_all(cov_list) == res


@pytest.mark.parametrize('x, y', [
    ('0/2', 1), ('1/2', 2), ('2/2', 0),
])
def test_branch_type(x, y):
    assert branch_type(x) == y
    assert branch_type(unicode(x)) == y


@pytest.mark.parametrize('line, _line_type', [
    (True, 2),
    (1, 0),
    (0, 1),
    (None, None),
    (False, None),
    (-1, -1),
    (u'0/2', 1),
    (str('1/2'), 2),
    (u'2/2', 0),
])
def test_line_type(line, _line_type):
    assert line_type(line) == _line_type


@pytest.mark.parametrize('lst, index, value, res', [
    ([1, 2, 3, 4, 5], 2, 10, [1, 2, 10, 4, 5]),
    ([1, 2, 3], 10, 5, [1, 2, 3, None, None, None, None, None, None, None, 5]),
])
def test_zfill(lst, index, value, res):
    assert zfill(lst, index, value) == res


@pytest.mark.parametrize('lines, res', [
    ([None, 0, 1, 2], {1: 0, 2: 1, 3: 2}),
    ({'1': 0, '2': 1, '3': 2}, {1: 0, 2: 1, 3: 2}),
    ([None], {}),
    ({}, {})
])
def test_list_to_dict(lines, res):
    assert json(list_to_dict(lines)) == json(res)


@pytest.mark.parametrize('b1, b2, res', [
    (u'1/2', u'2/2',  u'2/2'),
    (u'0/2', u'2/2',  u'2/2'),
    (u'0/2',      1,       1),
    (u'0/2',     -1,      -1),
    (0,       '2/2',   '2/2'),
    (True,    '2/2',   '2/2'),
    (None,    '2/2',   '2/2'),
    ('1/2',   '2/3',   '2/3'),
    (u'0/2', u'0/2',  u'0/2'),
    (u'0/2', u'0/2',  u'0/2'),
    (u'0/2', [[1, 2, None]], [[1, 2, None]]),
    ([[1, 2, None]], u'0/2', [[1, 2, None]]),
])
def test_merge_branch(b1, b2, res):
    assert res == merge_branch(b1, b2), '%s <> %s expected %s got %s' % (b1, b2, res, str(merge_branch(b1, b2)))
    assert res == merge_branch(b2, b1), '%s <> %s expected %s got %s' % (b2, b1, res, str(merge_branch(b2, b1)))


@pytest.mark.parametrize('partials, res', [
    ([(1, 5, 1), (5, 7, 0), (8, 9, 0)], '1/3'),
    ([(1, None, 1)], 1),
    ([(0, None, 1)], 1),
    ([(15, 18, 1)], 1),
    ([(1, None, 0)], 0),
    ([(0, None, 0)], 0),
    ([(0, 1, 0), (2, 3, 0)], '0/2'),
    ([(0, 1, 1), (3, 4, 1)], '2/2')
])
def test_partials_to_line(partials, res):
    assert res == partials_to_line(partials)


@pytest.mark.parametrize('p1, p2, res', [
    ([], [[1, 2, 3]], [[1, 2, 3]]),
    ([[1, None, 1]], [], [[1, None, 1]]),  # one
    ([[1, None, 1]], [[3, 5, 1]], [[1, None, 1]]),  # [--++--] inner join 1+&1 3-5&1 => 1+&1
    ([[1, None, 1]], [[1, 2, 0]], [[1, None, 1]]),  # [--++--] inner join 1+&1 1-2&0 => 1+&1
    ([[None, 10, 1]], [[None, 20, 1]], [[0, 20, 1]]),  # [++--] inner join -10&1 -20&1 => -20&1
    ([[None, 10, 0]], [[None, 20, 0]], [[0, 20, 0]]),  # [++--] inner join -10&1 10-20&0 => same
    ([[1, 5, 0], [6, 10, 1]], [[10, 15, 1], [18, 20, 0]], [[1, 5, 0], [6, 15, 1], [18, 20, 0]]),  # side join
    ([[0, 5, 1]], [[10, 20, 0]], [[0, 5, 1], [10, 20, 0]]),  # [-- --] outer join
    ([[None, 10, 0]], [[5, 20, 1]], [[0, 4, 0], [5, 20, 1]]),  # [--/--] reduce left
    ([[None, 10, 1]], [[5, 20, 0]], [[0, 10, 1], [11, 20, 0]]),  # [--/--] reduce right
])
def test_merge_partial_lines(p1, p2, res):
    assert res == merge_partial_line(p1, p2)
    assert res == merge_partial_line(p2, p1)


@pytest.mark.parametrize('l1, l2, brm, res', [
    (1, 5, None, 5),
    (1, 0, None, 1),
    (True, False, None, True),
    (False, True, None, True),
    (1, None, None, 1),
    ('0/3', '0/3', ['1:12', '1:3', '10:22', '10:12'], '0/3'),
    (99999, 10, None, 99999),
    (0, [[1, 1, 0]], None, 0),
    (0, [[1, 1, 1]], None, 1),
    ([[1, 1, 0]], 0, None, 0),
    ([[1, 1, 1]], 0, None, 1),
    (0, -1, None, -1),
    ('1/2', '2/2', None, '2/2'),
    ('0/2', '2/2', None, '2/2'),
    ('1/2', '1/2', None, '1/2'),
    ('1/2', '1/2', [], '2/2'),
    ('1/2', '1/2', None, '1/2'),
    ('1/2', '1/2', ['56'], '1/2'),
    ('1/4', '1/4', ['56'], '3/4'),
    ('1/4', 0, None, '1/4'),
    ('0/4', '0/4', None, '0/4'),
    ('1/4', 1, None, '4/4'),
    (0, 0, None, 0)
])
def test_merge_coverage(l1, l2, brm, res):
    assert merge_coverage(l1, l2, brm) == res
    assert merge_coverage(l2, l1, brm) == res


@pytest.mark.parametrize('totals, res', [
    ([ReportTotals(), ReportTotals(3, 3, 3, 3), ReportTotals()], ReportTotals(3, 3, 3, 3, 0, '100')),
    ([ReportTotals()], ReportTotals(1, 0, 0, 0, 0, '100'))
])
def test_sum_totals(totals, res):
    assert sum_totals(totals) == res


@pytest.mark.parametrize('sessions, res', [
    ([LineSession(1, 0, [1, 2, 3]), LineSession(1, 0, [2, 3])], [2, 3]),  # 2,3 missing
    ([LineSession(1, 0, [1, 2]), LineSession(1, 0, [1, 2])], [1, 2]),  # 1,2 missing
    ([LineSession(1, 0, [1, 2]), LineSession(1, 0, [3, 4])], []),  # 1,2 & 3,4 = []
    ([LineSession(1, 0, [1, 2]), LineSession(1, 0, [])], []),  # no branches missing on right
    ([LineSession('1/3', 0, [1, 2]), LineSession(1, 1)], []),  # because its a hit
    ([LineSession(1, 0, [1, 2]), LineSession(0, 0)], [1, 2]),  # missed = carry over branches
    ([LineSession(1, 0), LineSession(1, 1)], None),
    ([], None),
    ([LineSession(1, 0, [1, 2])], [1, 2])
])
def test_merge_missed_branches(sessions, res):
    assert merge_missed_branches(sessions) == res
    sessions.reverse()
    assert merge_missed_branches(sessions) == res


@pytest.mark.parametrize('l1, l2, res', [
    (None, (1, ), (1, )),  # no line to merge

    # sessions
    (('1/2', None, [[1, '1/2', ['1']]]),
    ('1/2', None, [[1, '1/2', ['2']]]),
    ('2/2', None, [LineSession(1, '2/2', [])])),

    # session, w/ single mb
    (('1/2', None, [[1, '1/2', ['1']]]),
    ('1/2', None, [[1, '1/2', ['1']]]),
    ('1/2', None, [LineSession(1, '1/2', ['1'])])),

    # different sessions
    (('1/2', None, [[1, '1/2', ['1']]]),
    ('1/2', None, [[2, '1/2', ['2']]]),
    ('2/2', None, [LineSession(1, '1/2', ['1']),
                    LineSession(2, '1/2', ['2'])])),
    # add coverage
    ((1, None, [[1, 1]]),
    (2, None, [[1, 2]]),
    (2, None, [LineSession(1, 2)])),

    # merge sessions
    (('2/2', None, [[1, '2/2']]),
    ('0/2', None, [[2, '0/2', [1, 2]]]),
    ('2/2', None, [LineSession(1, '2/2'),
                    LineSession(2, '0/2', [1, 2])])),

    # types
    ((1, None, [[1, 1]]),
    (1, 'b', [[1, 1]]),
    (1, 'b', [LineSession(1, 1)])),

    # messages
    # ((0, None, None, [{'s': '1', 't': 'a'}], 's': {'1': {'c': 0}}},
    #  (1, None, None, [{'s': '1', 't': 'a'}], 's': {'1': {'c': 1}}},
    #  (1, None, None, [{'s': '1', 't': 'a'}, {'s':
])
def test_merge_line(l1, l2, res):
    assert merge_line(ReportLine(*l1) if l1 else None, ReportLine(*l2) if l2 else None) == ReportLine(*res)
    res = merge_line(ReportLine(*l2) if l2 else None, ReportLine(*l1) if l1 else None)
    try:
        assert res == ReportLine(*res)
    except:
        res[2].reverse()
        assert res == ReportLine(*res)


@pytest.mark.parametrize('s1, s2, res', [
    (LineSession(0, '1/2', ['exit']), LineSession(0, '2/2'), LineSession(0, '2/2', [])),
    (LineSession(0, '1/2'), LineSession(0, '2/2'), LineSession(0, '2/2')),
    (LineSession(0, '1/2', ['exit']), LineSession(0, '1/2', ['1']), LineSession(0, '2/2', [])),
    (LineSession(0, '2/3', ['1']), LineSession(0, '1/3', ['1', '2']), LineSession(0, '2/3', ['1'])),
])
def test_merge_line_session(s1, s2, res):
    assert merge_line_session(s1, s2) == res
    assert merge_line_session(s2, s1) == res


@pytest.mark.parametrize('cov, res', [
    (1, False), (True, True), ('1/2', True)
])
def test_is_branch(cov, res):
    assert res == is_branch(cov)


@pytest.mark.parametrize('br, res', [
    (True, 2), ('1/4', 4), ('4/4', 4)
])
def test_branch_value(br, res):
    assert res == branch_value(br)


@pytest.mark.parametrize('totals, res', [
    ([None, xrange(6), xrange(6)], [2, 2, 4, 6, 8, '200.00000']),
    ([None, ReportTotals(*range(6)), ReportTotals(*range(6))], [2, 2, 4, 6, 8, '200.00000', 0, 0, 0, 0, 0, 0, 0]),
    ([], list((0, ) * 13))
])
def test_agg_totals(totals, res):
    assert agg_totals(totals) == res


def test_dumps_not_none():
    assert dumps_not_none(None) == ''
    assert dumps_not_none([1]) == '[1]'


def test_report_file_merge_rb_boiling_before():
    file1 = ReportFile('~.rb', lines=[ReportLine(coverage=0), ReportLine(coverage=0), ReportLine(coverage=0)])
    file2 = ReportFile('~.rb', lines=[None, ReportLine(coverage=1)])
    assert file1.merge(file2) is True, 'did merge'
    assert file1._totals is None, 'should remove totals cache'
    assert len(file1._lines) == 2, 'should only be 2 lines'
    assert file1._lines.count(None) == 1, 'should only have '
    assert file1.get(1) is None, 'line 1 is empty'
    assert file1[2].coverage == 1, 'line 2 should be hit'


def test_report_file_merge_rb_boiling_after():
    file1 = ReportFile('~.rb', lines=[None, ReportLine(coverage=1)])
    totals = file1._totals = Mock()
    file2 = ReportFile('~.rb', lines=[ReportLine(coverage=0), ReportLine(coverage=0), ReportLine(coverage=0)])
    assert file1.merge(file2) is False, 'did not merge'
    assert file1._totals == totals, 'should not remove totals cache'
    assert len(file1._lines) == 2, 'should only be 2 lines'
    assert file1._lines.count(None) == 1, 'should only have '
    assert file1.get(1) is None, 'line 1 is empty'
    assert file1[2].coverage == 1, 'line 2 should be hit'


def test_report_ignore_lines():
    r = Report()
    r.append(ReportFile('a', lines=[ReportLine(coverage=1), ReportLine(coverage=1)]))
    r.ignore_lines({'a': {'lines': {1, 20}}})
    with pytest.raises(IndexError):
        r['a'][1]
    assert r['a'][2].coverage == 1


def test_report_file_ignore_lines():
    f = ReportFile('a', lines=[ReportLine(coverage=1), ReportLine(coverage=1), ReportLine(coverage=1)])
    f.ignore_lines(lines={1}, eof=2)
    with pytest.raises(IndexError):
        f[1]
    assert f[2].coverage == 1
    with pytest.raises(IndexError):
        f[3]
    assert len(f._lines) == 2


def test_file_ignore_lines():
    _file = ReportFile('a', ignore={'lines': xrange(10, 20), 'eof': 50})
    for ln in xrange(1, 10):
        assert _file.append(ln, ReportLine(1))
        _file[ln] = ReportLine(1)
        assert _file.get(ln)

    for ln in xrange(10, 20):
        assert not _file.append(ln, ReportLine(1))
        _file[ln] = ReportLine(1)
        assert not _file.get(ln)

    for ln in xrange(100, 110):
        assert not _file.append(ln, ReportLine(1))
        _file[ln] = ReportLine(1)
        assert not _file.get(ln)

def test_maxint():
    assert maxint('123456') == 99999
    assert maxint('0') == 0
    assert maxint('123') == 123


def test_get_paths_from_flags():
    assert get_paths_from_flags(None, None) == []
    assert get_paths_from_flags({'yaml': {'flags': {'a': {'paths': ['b']}}}}, ['a']) == ['b']
    assert get_paths_from_flags({'yaml': {'flags': {'a': {'paths': ['b']}}}}, ['c']) == []


def test_assume_flags():
    report = Report()
    report.add_session(Session())
    report.append(ReportFile('a', lines=[ReportLine(0)]))
    report.append(ReportFile('b', lines=[ReportLine(1)]))

    report2 = Report()
    report2.add_session(Session(flags=['a']))
    report2.append(ReportFile('a', lines=[ReportLine(1, sessions=[[0, 1]])]))
    report2.append(ReportFile('b', lines=[None, ReportLine(1, sessions=[[0, 1]])]))
    report2.append(ReportFile('c', lines=[ReportLine(1, sessions=[[0, 1]])]))

    report.assume_flags(['a'], report2)

    assert len(report.sessions) == 2, 'There should be two sesisons on master report'
    assert report.sessions[1].name == 'Assumed', 'The last session should be the assumed one'
    assert report['a'][1].coverage == 1, 'Line a:1 should be covered'
    assert report['b'][1].coverage == 1, 'Line b:1 should be covered'
    assert report['b'][2].coverage == 1, 'Line b:2 should exist'
    assert report['c'][1].coverage == 1, 'File c should exist'


def test_report_has_flag():
    report = Report(sessions={1: dict(flags=['a'])})
    assert report.has_flag('a')
    assert not report.has_flag('b')
