import pytest
from src.utils.tuples import ReportTotals, ReportLine
from src.Report import Report, ReportFile


def test_report_repr():
    assert repr(Report()) == '<Report files=0>'


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


def test_get():
    r = Report(files={
        'file.py': [0, ReportTotals(1)]
    })
    assert repr(r.get('file.py')) == '<ReportFile name=file.py lines=0>'

    r2 = Report(files={
        'file.py': [0, ReportTotals(1)]
    }).filter(paths=['py.py'])

    assert r2.get('file.py') is None

    r3 = Report(files={
        'file.py': [0, ReportTotals(1)]
    }, chunks='null\n[1]\n[1]\n[1]\n<<<<< end_of_chunk >>>>>\nnull\n[1]\n[1]\n[1]')

    assert repr(r3.get('file.py')) == '<ReportFile name=file.py lines=3>'


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
