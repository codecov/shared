import pytest
from tests.helper import v2_to_v3
from src.utils.tuples import ReportTotals, ReportLine, NetworkFile
from src.helpers.sessions import Session
from src.ReportFile import ReportFile
from src.Report import Report, get_complexity_from_sessions


def test_report_repr():
    assert repr(Report()) == '<Report files=0>'


@pytest.mark.parametrize('r, network', [
    (Report(files={
        'py.py': [0, ReportTotals(1)]
    }),
     [('py.py', NetworkFile(totals=ReportTotals(1), session_totals=None, diff_totals=None))]),
    (Report(files={
        'py.py': [0, ReportTotals(1, 1, 1, 1, 1, 1)]
    }, chunks='null\n[1]\n[1]\n[1]\n<<<<< end_of_chunk >>>>>\nnull\n[1]\n[1]\n[1]').filter(paths=['py.py']),
     [('py.py', NetworkFile(totals=ReportTotals(1, 1, 1, 1, 1, 1), session_totals=None, diff_totals=None))])
])
def test_network(r, network):
    assert list(r.network) == network


@pytest.mark.parametrize('r', [
    (Report(files={
        'py.py': [0, ReportTotals(1)]
    })),
    (Report(files={
        'py.py': [0, ReportTotals(1)]
    }).filter(paths=['py.py']))
])
def test_files(r):
    assert r.files == ['py.py']


def test_ignore_lines():
    r = Report(files={
        'py.py': [0, ReportTotals(1)]
    }, chunks='null\n[1]\n[1]\n[1]\n<<<<< end_of_chunk >>>>>\nnull\n[1]\n[1]\n[1]')
    assert list(r.get('py.py').lines) == [(1, ReportLine(1)), (2, ReportLine(1)), (3, ReportLine(1))]
    r.ignore_lines({
        'py.py': {
            'lines': [0, 1, 2]
        }
    })
    # print list(r.get('py.py').lines) # TODO help here


def test_resolve_paths():
    r = Report(files={
        'py.py': [0, ReportTotals(1)]
    }, chunks='null\n[1]\n[1]\n[1]\n<<<<< end_of_chunk >>>>>\nnull\n[1]\n[1]\n[1]')
    assert r.files == ['py.py']
    r.resolve_paths([('py.py', 'file.py')])
    assert r.files == ['file.py']


@pytest.mark.parametrize('r, _file, joined, boolean, lines, hits', [
    (Report(), ReportFile('a', totals=ReportTotals(1, 50, 10), lines=[ReportLine(1)]), False, True, 50, 0),
    (Report(), None, True, False, 0, 0),
    (Report(), ReportFile('name.py'), True, False, 0, 0),
])
def test_append(r, _file, joined, boolean, lines, hits):
    assert r.append(_file, joined) is boolean
    assert r.totals.lines == lines
    assert r.totals.hits == hits


def test_append_error():
    r = Report()
    with pytest.raises(Exception) as e_info:
        r.append('str')
    assert e_info.value.message == "expecting ReportFile got <type 'str'>"


@pytest.mark.parametrize('r, file_repr', [
    (Report(files={
        'file.py': [0, ReportTotals(1)]
    }), '<ReportFile name=file.py lines=0>'),
    (Report(files={
        'file.py': [0, ReportTotals(1)]
    }).filter(paths=['py.py']), 'None'),
    (Report(files={
        'file.py': [0, ReportTotals(1)]
    }, chunks='null\n[1]\n[1]\n[1]\n<<<<< end_of_chunk >>>>>\nnull\n[1]\n[1]\n[1]'), '<ReportFile name=file.py lines=3>'),
    (Report(files={
        'file.py': [0, ReportTotals(1)]
    }, chunks=[ReportFile(name='file.py')]), '<ReportFile name=file.py lines=0>'),
])
def test_get(r, file_repr):
    assert repr(r.get('file.py')) == file_repr


def test_rename():
    r = Report(files={
        'file.py': [0, ReportTotals(1)]
    }, chunks='null\n[1]\n[1]\n[1]\n<<<<< end_of_chunk >>>>>\nnull\n[1]\n[1]\n[1]')
    assert r.get('name.py') is None
    assert repr(r.get('file.py')) == '<ReportFile name=file.py lines=3>'
    assert r.rename('file.py', 'name.py') is True
    assert r.get('file.py') is None
    assert repr(r.get('name.py')) == '<ReportFile name=name.py lines=3>'


def test_get_item():
    r = Report(files={
        'file.py': [0, ReportTotals(1)]
    })
    assert repr(r['file.py']) == '<ReportFile name=file.py lines=0>'


def test_get_item_exception():
    r = Report(files={
        'file.py': [0, ReportTotals(1)]
    })
    with pytest.raises(Exception) as e_info:
        r['name.py']
    assert e_info.value.message == 'File at path name.py not found in report'


def test_del_item():
    r = Report(files={
        'file.py': [0, ReportTotals(1)]
    }, chunks='null\n[1]\n[1]\n[1]\n<<<<< end_of_chunk >>>>>\nnull\n[1]\n[1]\n[1]')
    assert repr(r.get('file.py')) == '<ReportFile name=file.py lines=3>'
    del r['file.py']
    assert r.get('file.py') is None


@pytest.mark.parametrize('r, manifest', [
    (Report(files={
        'file1.py': [0, ReportTotals(1)],
        'file2.py': [1, ReportTotals(1)]
    }), ['file1.py', 'file2.py']),
    (Report(files={
        'file1.py': [0, ReportTotals(1)],
        'file2.py': [1, ReportTotals(1)]
    }).filter(paths=['file2.py']), ['file2.py']),
])
def test_manifest(r, manifest):
    assert r.manifest == manifest


def test_flags():
    r = Report(files={
        'py.py': [0, ReportTotals(1)]
    }, sessions={1: {
        'id': 'id',
        'f': ['a', 1, 'test'],
    }})
    assert r.flags.keys() == ['a', 1, 'test']


def test_iter():
    r = Report(files={
        'file1.py': [0, ReportTotals(1)],
        'file2.py': [1, ReportTotals(1)]
    })
    files = []
    for _file in r:
        files.append(_file)
    assert repr(files) == '[<ReportFile name=file1.py lines=0>, <ReportFile name=file2.py lines=0>]'


def test_contains():
    r = Report(files={
        'file1.py': [0, ReportTotals(1)],
    })
    assert ('file1.py' in r) is True
    assert ('file2.py' in r) is False


@pytest.mark.parametrize('r, new_report, manifest', [
    (Report(files={
        'file.py': [0, ReportTotals(1)],
    }), None, ['file.py']),
    (Report(files={
        'file.py': [0, ReportTotals(1)],
    }), Report(), ['file.py']),
    (Report(files={
        'file.py': [0, ReportTotals(1)],
    }, chunks='null\n[1]\n[1]\n[1]\n<<<<< end_of_chunk >>>>>'), Report(files={
        'other-file.py': [1, ReportTotals(2)]
    }, chunks='null\n[1]\n[1]\n[1]\n<<<<< end_of_chunk >>>>>\nnull\n[1]\n[1]\n[1]'), ['other-file.py', 'file.py']),
])
def test_merge(r, new_report, manifest):
    assert r.manifest == ['file.py']
    r.merge(new_report)
    assert r.manifest == manifest


def test_merge_exception():
    r = Report(files={
        'file.py': [0, ReportTotals(1)],
    })
    with pytest.raises(Exception) as e_info:
        r.merge('str')
    assert e_info.value.message == "expecting type Report got <type 'str'>"


@pytest.mark.parametrize('r, boolean', [
    (Report(), True),
    (Report(files={
        'file.py': [0, ReportTotals(1)]
    }).filter(paths=['this-file.py']), True),
    (Report(files={
        'file.py': [0, ReportTotals(1)]
    }), False),
])
def test_is_empty(r, boolean):
    assert r.is_empty() is boolean


@pytest.mark.parametrize('r, boolean', [
    (Report(), False),
    (Report(files={
        'file.py': [0, ReportTotals(1)]
    }), True),
])
def test_non_zero(r, boolean):
    assert bool(r) is boolean


def test_to_archive():
    assert Report(files={
        'file.py': [0, ReportTotals()]
    }, chunks='null\n[1]\n[1]\n[1]\n<<<<< end_of_chunk >>>>>\nnull\n[1]\n[1]\n[1]').to_archive() ==\
           'null\n[1]\n[1]\n[1]\n<<<<< end_of_chunk >>>>>\nnull\n[1]\n[1]\n[1]'


def test_to_database():
    assert Report(files={
        'file.py': [0, ReportTotals()]
    }, chunks='null\n[1]\n[1]\n[1]\n<<<<< end_of_chunk >>>>>\nnull\n[1]\n[1]\n[1]').to_database() ==\
           ({'M': 0, 'c': '100', 'b': 0, 'd': 0, 'f': 1, 'h': 0, 'm': 0, 'C': 0, 'n': 0, 'p': 0, 's': 0, 'diff': None, 'N': 0}, '{"files": {"file.py": [0, [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]]}, "sessions": {}}')


@pytest.mark.parametrize('diff, future, future_diff, res', [
    ({}, None, None, False),  # empty
    (None, None, None, False),  # empty
    ({'files': {}}, None, None, False),  # empty
    ({'files': {'b': {'type': 'new'}}}, None, None, False),  # new file not tracked
    ({'files': {'b': {'type': 'new'}}}, {'files': {'b': {'l': {'1': {'c': 1}}}}}, None, True),  # new file is tracked
    ({'files': {'b': {'type': 'modified'}}}, None, None, False),  # file not tracked in base or head
    ({'files': {'a': {'type': 'deleted'}}}, None, None, True),  # tracked file deleted
    ({'files': {'b': {'type': 'deleted'}}}, None, None, False),  # not-tracked file deleted
    ({'files': {'z': {'type': 'modified'}}}, None, None, True),  # modified file missing in base
    ({'files': {'a': {'type': 'modified'}}}, None, None, True),  # modified file missing in head
    ({'files': {'a': {'type': 'modified', 'segments': [{'header': [0, 1, 1, 2], 'lines': ['- a', '+ a']}]}}},
     {'files': {'a': {'l': {'1': {'c': 1}}}}}, None, True),  # tracked line deleted
    ({'files': {'a': {'type': 'modified', 'segments': [{'header': [0, 1, 1, 2], 'lines': ['- a', '+ a']}]}}},
     {'files': {'a': {'l': {'1': {'c': 1}}}}},
     {'files': {'a': {'type': 'modified'}}},
     True),  # tracked line deleted
    ({'files': {'a': {'type': 'modified', 'segments': [{'header': [10, 1, 10, 2], 'lines': ['- a', '+ a']}]}}},
     {'files': {'a': {'l': {'1': {'c': 1}}}}}, None, False)  # lines not tracked`
])
def test_does_diff_adjust_tracked_lines(diff, future, future_diff, res):
    report = v2_to_v3({'files': {'a': {'l': {'1': {'c': 1}, '2': {'c': 1}}}}})
    if future:
        future = v2_to_v3(future)
    else:
        future = v2_to_v3({'files': {'z': {}}})

    assert report.does_diff_adjust_tracked_lines(diff, future, future_diff) == res

def test_apply_diff():
    report = v2_to_v3({'files': {'a': {'l': {'1': {'c': 1}, '2': {'c': 0}}}}})
    diff = {
        'files': {
            'a': {'type': 'new', 'segments': [{'header': list('1313'), 'lines': list('---+++')}]},
            'b': {'type': 'deleted'},
            'c': {'type': 'modified'}
        }
    }
    assert report.apply_diff(None) is None
    assert report.apply_diff({}) is None
    res = report.apply_diff(diff)
    assert res == diff['totals']
    assert diff['totals'].coverage == '50.00000'


def test_apply_diff_no_append():
    report = v2_to_v3({'files': {'a': {'l': {'1': {'c': 1}, '2': {'c': 0}}}}})
    diff = {
        'files': {
            'a': {'type': 'new', 'segments': [{'header': list('1313'), 'lines': list('---+++')}]},
            'b': {'type': 'deleted'},
            'c': {'type': 'modified'}
        }
    }
    res = report.apply_diff(diff, _save=False)
    assert 'totals' not in diff
    assert 'totals' not in diff['files']['a']
    assert 'totals' not in diff['files']['c']
    assert res.coverage == '50.00000'


def test_report_has_flag():
    report = Report(sessions={1: dict(flags=['a'])})
    assert report.has_flag('a')
    assert not report.has_flag('b')


@pytest.mark.parametrize('sessions, complexity', [
    ([[1, 2, 3, 4, 5]], 5),
    ([[[1, 2], [2, 3], [3, 4], [4, 5], [5, 6], [6, 7]]], (5, 6)),
])
def test_get_complexity_from_sessions(sessions, complexity):
    assert get_complexity_from_sessions(sessions) == complexity
    assert get_complexity_from_sessions(sessions) == complexity


def test_add_session():
    s = Session(5)
    r = Report(files={
        'file.py': [0, ReportTotals(0)]
    }, totals=ReportTotals(0))
    assert r.totals.sessions == 0
    assert r.sessions == {}
    assert r.add_session(s) == (0, s)
    assert r.totals.sessions == 1
    assert r.sessions == {0: s}


@pytest.mark.parametrize('r, params, flare', [
    (Report(files={
        'py.py': [0, ReportTotals(1)]
    }, chunks='null\n[1]\n[1]\n[1]\n<<<<< end_of_chunk >>>>>\nnull\n[1]\n[1]\n[1]'),
     {'color': lambda cov: 'purple' if cov is None else '#e1e1e1' if cov == 0 else 'green' if cov > 0 else 'red'},
     [{'name': '', 'coverage': 100, 'color': 'green', '_class': None, 'lines': 0, 'children': [{'color': '#e1e1e1', '_class': None, 'lines': 0, 'name': 'py.py', 'coverage': 0}]}]),
    (Report(files={
        'py.py': [0, ReportTotals(1)]
    }),
     {'changes': {}},
     [{'name': '', 'coverage': 100, 'color': 'green', '_class': None, 'lines': 0, 'children': [{'color': '#e1e1e1', '_class': None, 'lines': 0, 'name': 'py.py', 'coverage': 0}]}]),
])
def test_flare(r, params, flare):
    assert r.flare(**params) == flare


def test_filter():
    r = Report().filter(paths=['test/path/file.py'])
    assert r.get('wrong/test/path/file.py') is None

    r1 = Report(files={
        'file.py':[0, ReportTotals(1)]
    }, chunks='null\n[1]\n[1]\n[1]\n<<<<< end_of_chunk >>>>>\nnull\n[1]\n[1]\n[1]').filter(flags='test')
    # print r1.get('file.py')  # TODO better test


def test_filter_exception():
    with pytest.raises(Exception) as e_info:
        Report().filter(paths='str')
    assert e_info.value.message == "expecting list for argument paths got <type 'str'>"
