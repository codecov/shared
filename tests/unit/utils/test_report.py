import pytest
from src.reports import Report, ReportFile


def test_report_repr():
    assert repr(Report()) == '<Report files=0>'


def test_append_none():
    r = Report()
    r_test = Report()
    assert repr(r) == repr(r_test)
    assert r_test.append(None) == False
    assert repr(r) == repr(r_test)


def test_append_error():
    r = Report()
    with pytest.raises(Exception) as e_info:
        r.append('str')
    assert e_info.value.message == "expecting ReportFile got <type 'str'>"
    assert r.append(ReportFile('name.py')) == False


def test_get_filtered_out():
    r = Report().filter(paths=['test/path/file.py'])
    assert r.get('wrong/test/path/file.py') is None


def test_report_merge_none():
    r = Report()
    assert r.merge(None) is None
    with pytest.raises(Exception) as e_info:
        r.merge('str')
    assert e_info.value.message == "expecting type Report got <type 'str'>"
    assert r.merge(Report()) is None


def test_is_empty():
    r = Report().filter(['path/file.py'])
    assert r.is_empty() is True


def test_to_archive():
    END_OF_CHUNK = '\n<<<<< end_of_chunk >>>>>\n'
    chunk = 'null\n[1,1,1]\nnull'+END_OF_CHUNK+'null\nnull\n[1,1,1]\n[1,2,2,1]'
    r = Report(chunks=chunk)
    assert r.to_archive() == chunk


def test_to_database():
    r = Report(totals=[1, 1, 1, 2, ])
    assert r.to_database() == ({'M': 0, 'c': 0, 'b': 0, 'd': 0, 'f': 1, 'h': 1, 'm': 2, 'C': 0, 'n': 1, 'p': 0, 's': 0, 'diff': None, 'N': 0}, '{"files": {}, "sessions": {}}')
