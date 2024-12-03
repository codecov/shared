import pytest
from mock import PropertyMock

from shared.reports.editable import EditableReport, EditableReportFile
from shared.reports.exceptions import LabelIndexNotFoundError, LabelNotFoundError
from shared.reports.resources import (
    END_OF_CHUNK,
    Report,
    ReportFile,
    _encode_chunk,
    chunks_from_storage_contains_header,
)
from shared.reports.types import (
    CoverageDatapoint,
    LineSession,
    NetworkFile,
    ReportFileSummary,
    ReportHeader,
    ReportLine,
    ReportTotals,
)
from shared.utils.match import match
from shared.utils.sessions import Session, SessionType
from tests.helper import v2_to_v3


def report_with_file_summaries():
    return Report(
        files={
            "calc/CalcCore.cpp": ReportFileSummary(
                file_index=0,
                file_totals=ReportTotals(
                    files=0,
                    lines=10,
                    hits=7,
                    misses=2,
                    partials=1,
                    coverage="70.00000",
                    branches=6,
                    methods=4,
                    messages=0,
                    sessions=0,
                    complexity=0,
                    complexity_total=0,
                    diff=0,
                ),
                diff_totals=None,
            ),
            "calc/CalcCore.h": ReportFileSummary(
                file_index=1,
                file_totals=ReportTotals(
                    files=0,
                    lines=1,
                    hits=1,
                    misses=0,
                    partials=0,
                    coverage="100",
                    branches=0,
                    methods=1,
                    messages=0,
                    sessions=0,
                    complexity=0,
                    complexity_total=0,
                    diff=0,
                ),
                diff_totals=None,
            ),
            "calc/Calculator.cpp": ReportFileSummary(
                file_index=2,
                file_totals=ReportTotals(
                    files=0,
                    lines=4,
                    hits=3,
                    misses=1,
                    partials=0,
                    coverage="75.00000",
                    branches=1,
                    methods=1,
                    messages=0,
                    sessions=0,
                    complexity=0,
                    complexity_total=0,
                    diff=0,
                ),
                diff_totals=None,
            ),
        },
        totals=ReportTotals(
            files=3,
            lines=15,
            hits=11,
            misses=3,
            partials=1,
            coverage="73.33333",
            branches=7,
            methods=6,
            messages=0,
            sessions=0,
            complexity=0,
            complexity_total=0,
            diff=0,
        ),
    )


@pytest.mark.unit
def test_report_repr(mocker):
    r = Report()
    r._files = []
    assert repr(Report()) == "<Report files=0>"


@pytest.mark.unit
@pytest.mark.parametrize(
    "chunks, expected",
    [
        ("", False),
        ("{}\nline\nline\n\n", False),
        ("{}\nline\nline\n\n<<<<< end_of_chunk >>>>>\n{}\nline\nline\n", False),
        (
            "{}\n<<<<< end_of_header >>>>>\n{}\nline\nline\n\n<<<<< end_of_chunk >>>>>\n{}\nline\nline\n",
            True,
        ),
        ("{}\n<<<<< end_of_header >>>>>\n{}\nline\nline\n\n", True),
        ("{}\n<<<<< end_of_header >>>>>\n", True),
    ],
)
def test_chunks_from_storage_contains_header(chunks, expected):
    assert chunks_from_storage_contains_header(chunks) == expected


@pytest.mark.unit
@pytest.mark.parametrize(
    "files, chunks, path_filter, network",
    [
        (
            {"py.py": [0, ReportTotals(1)]},
            [],
            None,
            [
                (
                    "py.py",
                    NetworkFile(totals=ReportTotals(1), diff_totals=None),
                )
            ],
        ),
        (
            {"py.py": [0, ReportTotals(1, 1, 1, 1, 1, 1)]},
            "null\n[1]\n[1]\n[1]\n<<<<< end_of_chunk >>>>>\nnull\n[1]\n[1]\n[1]".split(
                END_OF_CHUNK
            ),
            lambda filename: match(["py.py"], filename),
            [
                (
                    "py.py",
                    NetworkFile(
                        totals=ReportTotals(1, 1, 1, 1, 1, 1),
                        diff_totals=None,
                    ),
                )
            ],
        ),
    ],
)
def test_network(files, mocker, chunks, path_filter, network):
    r = Report(files=files)
    r._chunks = chunks
    r._path_filter = path_filter
    r._line_modifier = None
    assert list(r.network) == network


@pytest.mark.unit
@pytest.mark.parametrize(
    "files, path_filter",
    [
        ({"py.py": [0, ReportTotals(1)]}, None),
        ({"py.py": [0, ReportTotals(1)]}, lambda filename: match(["py.py"], filename)),
    ],
)
def test_files(files, path_filter):
    r = Report(files=files)
    r._path_filter = path_filter
    assert r.files == ["py.py"]


@pytest.mark.unit
def test_resolve_paths(mocker):
    r = Report(files={"py.py": [0, ReportTotals(1)]})
    r._path_filter = None
    r._chunks = (
        "null\n[1]\n[1]\n[1]\n<<<<< end_of_chunk >>>>>\nnull\n[1]\n[1]\n[1]".split(
            END_OF_CHUNK
        )
    )
    assert r.files == ["py.py"]
    r.resolve_paths([("py.py", "file.py")])
    assert r.files == ["file.py"]


@pytest.mark.unit
@pytest.mark.parametrize(
    "r, _file, joined, boolean, lines, hits",
    [
        (
            Report(),
            ReportFile(
                "a", totals=ReportTotals(1, 50, 10), lines=[ReportLine.create(1)]
            ),
            False,
            True,
            50,
            0,
        ),
        (Report(), None, True, False, 0, 0),
        (Report(), ReportFile("name.py"), True, False, 0, 0),
    ],
)
def test_append(r, _file, joined, boolean, lines, hits):
    assert r.append(_file, joined) is boolean
    assert r.totals.lines == lines
    assert r.totals.hits == hits


@pytest.mark.unit
def test_append_error(mocker):
    r = Report()
    with pytest.raises(Exception) as e_info:
        r.append("str")
    assert str(e_info.value) == "expecting ReportFile got <class 'str'>"


@pytest.mark.unit
@pytest.mark.parametrize(
    "files, chunks, file_repr, lines",
    [
        (
            {"file.py": [0, ReportTotals(1)]},
            None,
            "<ReportFile name=file.py lines=0>",
            [],
        ),
        ({"py.py": [0, ReportTotals(1)]}, None, "None", None),
        (
            {"file.py": [0, ReportTotals(1)]},
            "null\n[1]\n[1]\n[1]\n<<<<< end_of_chunk >>>>>\nnull\n[1]\n[1]\n[1]".split(
                END_OF_CHUNK
            ),
            "<ReportFile name=file.py lines=3>",
            [
                (1, ReportLine.create(1)),
                (2, ReportLine.create(1)),
                (3, ReportLine.create(1)),
            ],
        ),
        (
            {"file.py": [0, ReportTotals(1)]},
            [ReportFile(name="file.py")],
            "<ReportFile name=file.py lines=0>",
            [],
        ),
        (
            {"file.py": [1, ReportTotals(1)]},
            [ReportFile(name="other-file.py")],
            "<ReportFile name=file.py lines=0>",
            [],
        ),
    ],
)
def test_get(files, chunks, file_repr, lines):
    r = Report(files=files)
    r._chunks = chunks
    r._line_modifier = None

    assert repr(r.get("file.py")) == file_repr
    if lines:
        assert list(r.get("file.py").lines) == lines


@pytest.mark.unit
def test_rename(mocker):
    r = Report(files={"file.py": [0, ReportTotals(1)]})
    r._path_filter = None
    r._line_modifier = None
    r._chunks = (
        "null\n[1]\n[1]\n[1]\n<<<<< end_of_chunk >>>>>\nnull\n[1]\n[1]\n[1]".split(
            END_OF_CHUNK
        )
    )
    assert r.get("name.py") is None
    assert repr(r.get("file.py")) == "<ReportFile name=file.py lines=3>"
    assert r.rename("file.py", "name.py") is True
    assert r.get("file.py") is None
    assert repr(r.get("name.py")) == "<ReportFile name=name.py lines=3>"


@pytest.mark.unit
def test_get_item(mocker):
    r = Report()
    r._files = PropertyMock(return_value={"file.py": [0, ReportTotals(1)]})
    r._chunks = None
    r._path_filter = None
    r._line_modifier = None
    assert repr(r["file.py"]) == "<ReportFile name=file.py lines=0>"


@pytest.mark.unit
def test_get_item_exception(mocker):
    r = Report()
    r._files = {"file.py": [0, ReportTotals(1)]}
    r._path_filter = None
    r._line_modifier = None
    r._chunks = None
    with pytest.raises(Exception) as e_info:
        r["name.py"]
    assert str(e_info.value) == "File at path name.py not found in report"


@pytest.mark.unit
def test_del_item(mocker):
    r = Report(files={"file.py": [0, ReportTotals(1)]})
    r._path_filter = None
    r._line_modifier = None
    r._chunks = (
        "null\n[1]\n[1]\n[1]\n<<<<< end_of_chunk >>>>>\nnull\n[1]\n[1]\n[1]".split(
            END_OF_CHUNK
        )
    )
    assert repr(r.get("file.py")) == "<ReportFile name=file.py lines=3>"
    del r["file.py"]
    assert r.get("file.py") is None


@pytest.mark.unit
def test_manifest():
    r = Report()
    r._files = {"file1.py": [0, ReportTotals(1)], "file2.py": [1, ReportTotals(1)]}
    r._chunks = None
    r._line_modifier = None
    assert list(r.files) == ["file1.py", "file2.py"]


@pytest.mark.unit
class TestReportHeader(object):
    def test_default(self):
        r = Report()
        assert r.header == ReportHeader()
        assert r.labels_index is None

    def test_get(self):
        r = Report()
        r._header = ReportHeader(labels_index={0: "special_label"})
        assert r.header == ReportHeader(labels_index={0: "special_label"})

    def test_from_archive(self):
        r = Report(
            files={"other-file.py": [1, ReportTotals(2)]},
            chunks='{"labels_index":{"0": "special_label"}}\n<<<<< end_of_header >>>>>\nnull\n[1]\n[1]\n[1]\n<<<<< end_of_chunk >>>>>\nnull\n[1]\n[1]\n[1]',
        )
        assert r.header == ReportHeader(labels_index={0: "special_label"})

    def test_setter(self):
        r = Report()
        header = ReportHeader(labels_index={0: "special_label"})
        r.header = header
        assert r.header == header

    def test_get_labels_index(self):
        r = Report()
        r._header = ReportHeader(labels_index={0: "special_label"})
        assert r.labels_index == {0: "special_label"}

    def test_set_labels_index(self):
        r = Report()
        assert r.labels_index is None
        r.labels_index = {0: "special_label"}
        assert r.labels_index == {0: "special_label"}
        assert r.header == ReportHeader(labels_index={0: "special_label"})

    def test_partial_set_labels_index(self):
        r = Report()
        r._header = ReportHeader(labels_index={0: "special_label"})
        assert r.labels_index == {0: "special_label"}
        r.labels_index[1] = "some_test"
        r.labels_index == {0: "special_label", 1: "some_test"}


@pytest.mark.unit
def test_get_file_totals(mocker):
    report = report_with_file_summaries()
    report._path_filter = None

    expected_totals = ReportTotals(
        files=0,
        lines=10,
        hits=7,
        misses=2,
        partials=1,
        coverage="70.00000",
        branches=6,
        methods=4,
        messages=0,
        sessions=0,
        complexity=0,
        complexity_total=0,
        diff=0,
    )
    assert report.get_file_totals("calc/CalcCore.cpp") == expected_totals


@pytest.mark.unit
def test_flags(mocker):
    r = Report()
    r._files = {"py.py": [0, ReportTotals(1)]}
    r._chunks = None
    r._path_filter = None
    r._line_modifier = None
    r.sessions = {
        1: Session(flags={"a": 1, 1: 1, "test": 1}),
        2: Session(
            flags=["c"],
            session_type=SessionType.carriedforward,
            session_extras=dict(carriedforward_from="commit_SHA"),
        ),
    }
    assert list(r.flags.keys()) == ["a", 1, "test", "c"]
    for name, flag in r.flags.items():
        assert flag.carriedforward is (True if name == "c" else False)
        assert flag.carriedforward_from is ("commit_SHA" if name == "c" else None)


@pytest.mark.unit
def test_iter(mocker):
    r = Report(
        files={"file1.py": [0, ReportTotals(1)], "file2.py": [1, ReportTotals(1)]}
    )
    r._chunks = None
    r._path_filter = None
    r._line_modifier = None
    files = [_file for _file in r]
    assert (
        repr(files)
        == "[<ReportFile name=file1.py lines=0>, <ReportFile name=file2.py lines=0>]"
    )


@pytest.mark.unit
def test_contains(mocker):
    r = Report()
    r._files = {"file1.py": [0, ReportTotals(1)]}
    assert ("file1.py" in r) is True
    assert ("file2.py" in r) is False


def test_get_label_from_idx():
    report = Report()
    label_idx = {0: "Special_global_label", 1: "banana", 2: "cachorro"}
    report._header = ReportHeader(labels_index=label_idx)
    report_file = ReportFile(
        name="something.py",
        lines=[
            ReportLine.create(
                coverage=1,
                type=None,
                sessions=[[0, 1]],
                datapoints=[
                    CoverageDatapoint(
                        sessionid=0, coverage=1, coverage_type=None, label_ids=[0, 2]
                    )
                ],
            )
        ],
    )
    report.append(report_file)
    labels_in_report = set()
    for file in report:
        for line in file:
            for datapoint in line.datapoints:
                for label_id in datapoint.label_ids:
                    labels_in_report.add(report.lookup_label_by_id(label_id))
    assert "Special_global_label" in labels_in_report
    assert "cachorro" in labels_in_report
    assert "banana" not in labels_in_report


def test_lookup_label_by_id_fails():
    report = Report()
    with pytest.raises(LabelIndexNotFoundError):
        report.lookup_label_by_id(0)

    label_idx = {0: "Special_global_label", 1: "banana", 2: "cachorro"}
    report._header = ReportHeader(labels_index=label_idx)

    with pytest.raises(LabelNotFoundError):
        report.lookup_label_by_id(100)


@pytest.mark.unit
@pytest.mark.parametrize(
    "files, chunks, new_report, manifest",
    [
        ({"file.py": [0, ReportTotals(1)]}, None, None, ["file.py"]),
        ({"file.py": [0, ReportTotals(1)]}, None, Report(), ["file.py"]),
        (
            {"file.py": [0, ReportTotals(1)]},
            "null\n[1]\n[1]\n[1]\n<<<<< end_of_chunk >>>>>".split(END_OF_CHUNK),
            Report(
                files={"other-file.py": [1, ReportTotals(2)]},
                chunks="null\n[1]\n[1]\n[1]\n<<<<< end_of_chunk >>>>>\nnull\n[1]\n[1]\n[1]",
            ),
            ["file.py", "other-file.py"],
        ),
    ],
)
def test_merge(files, chunks, new_report, manifest):
    r = Report(files=files)
    r._chunks = chunks
    r._path_filter = None
    r._line_modifier = None
    r.sessions = {}
    r._filter_cache = (None, None)
    assert list(r.files) == ["file.py"]
    r.merge(new_report)
    assert list(r.files) == manifest


@pytest.mark.unit
def test_merge_into_editable_report():
    editable_report = EditableReport(
        files={"file.py": [1, ReportTotals(2)]},
        chunks="null\n[1]\n[1]\n[1]\n<<<<< end_of_chunk >>>>>\nnull\n[1]\n[1]\n[1]",
    )
    new_report = Report(
        files={"other-file.py": [1, ReportTotals(2)]},
        chunks="null\n[1]\n[1]\n[1]\n<<<<< end_of_chunk >>>>>\nnull\n[1]\n[1]\n[1]",
    )
    editable_report.merge(new_report)
    assert list(editable_report.files) == ["file.py", "other-file.py"]
    for file in editable_report:
        assert isinstance(file, EditableReportFile)


@pytest.mark.unit
@pytest.mark.parametrize(
    "files, boolean", [({}, True), ({"file.py": [0, ReportTotals(1)]}, False)]
)
def test_is_empty(files, boolean):
    r = Report()
    r._files = files
    r._chunks = None
    assert r.is_empty() is boolean


@pytest.mark.unit
@pytest.mark.parametrize(
    "files, boolean", [({}, False), ({"file.py": [0, ReportTotals(1)]}, True)]
)
def test_non_zero(files, boolean):
    r = Report()
    r._files = files
    r._chunks = None
    r._path_filter = None
    assert bool(r) is boolean


@pytest.mark.unit
def test_to_archive(mocker):
    r = Report()
    r._files = PropertyMock(return_value={"file.py": [0, ReportTotals()]})
    r._chunks = (
        "null\n[1]\n[1]\n[1]\n<<<<< end_of_chunk >>>>>\nnull\n[1]\n[1]\n[1]".split(
            END_OF_CHUNK
        )
    )
    assert (
        r.to_archive()
        == "{}\n<<<<< end_of_header >>>>>\nnull\n[1]\n[1]\n[1]\n<<<<< end_of_chunk >>>>>\nnull\n[1]\n[1]\n[1]"
    )


@pytest.mark.unit
def test_to_archive_with_header(mocker):
    r = Report()
    r._files = PropertyMock(return_value={"file.py": [0, ReportTotals()]})
    r._header = ReportHeader(labels_index={0: "special_label", 1: "some_label"})
    r._chunks = (
        "null\n[1]\n[1]\n[1]\n<<<<< end_of_chunk >>>>>\nnull\n[1]\n[1]\n[1]".split(
            END_OF_CHUNK
        )
    )
    assert (
        r.to_archive()
        == '{"labels_index":{"0":"special_label","1":"some_label"}}\n<<<<< end_of_header >>>>>\nnull\n[1]\n[1]\n[1]\n<<<<< end_of_chunk >>>>>\nnull\n[1]\n[1]\n[1]'
    )


@pytest.mark.unit
def test_to_database(mocker):
    r = Report(files={"file.py": [0, ReportTotals()]})
    r._chunks = (
        "null\n[1]\n[1]\n[1]\n<<<<< end_of_chunk >>>>>\nnull\n[1]\n[1]\n[1]".split(
            END_OF_CHUNK
        )
    )
    r._totals = None
    r.diff_totals = None
    r.sessions = {}
    r._path_filter = None
    r._line_modifier = None
    r._filter_cache = (None, None)
    assert r.to_database() == (
        {
            "M": 0,
            "c": None,
            "b": 0,
            "d": 0,
            "f": 1,
            "h": 0,
            "m": 0,
            "C": 0,
            "n": 0,
            "p": 0,
            "s": 0,
            "diff": None,
            "N": 0,
        },
        '{"files":{"file.py":[0,[0,0,0,0,0,0,0,0,0,0,0,0,0],null,null]},"sessions":{}}',
    )


@pytest.mark.unit
@pytest.mark.parametrize(
    "diff, future, future_diff, res",
    [
        ({}, None, None, False),  # empty
        (None, None, None, False),  # empty
        ({"files": {}}, None, None, False),  # empty
        ({"files": {"b": {"type": "new"}}}, None, None, False),  # new file not tracked
        (
            {"files": {"b": {"type": "new"}}},
            {"files": {"b": {"l": {"1": {"c": 1}}}}},
            None,
            True,
        ),  # new file is tracked
        (
            {"files": {"b": {"type": "modified"}}},
            None,
            None,
            False,
        ),  # file not tracked in base or head
        (
            {"files": {"a": {"type": "deleted"}}},
            None,
            None,
            True,
        ),  # tracked file deleted
        (
            {"files": {"b": {"type": "deleted"}}},
            None,
            None,
            False,
        ),  # not-tracked file deleted
        (
            {"files": {"z": {"type": "modified"}}},
            None,
            None,
            True,
        ),  # modified file missing in base
        (
            {"files": {"a": {"type": "modified"}}},
            None,
            None,
            True,
        ),  # modified file missing in head
        (
            {
                "files": {
                    "a": {
                        "type": "modified",
                        "segments": [{"header": [0, 1, 1, 2], "lines": ["- a", "+ a"]}],
                    }
                }
            },
            {"files": {"a": {"l": {"1": {"c": 1}}}}},
            None,
            True,
        ),  # tracked line deleted
        (
            {
                "files": {
                    "a": {
                        "type": "modified",
                        "segments": [{"header": [0, 1, 1, 2], "lines": ["- a", "+ a"]}],
                    }
                }
            },
            {"files": {"a": {"l": {"1": {"c": 1}}}}},
            {"files": {"a": {"type": "modified"}}},
            True,
        ),  # tracked line deleted
        (
            {
                "files": {
                    "a": {
                        "type": "modified",
                        "segments": [
                            {"header": [10, 1, 10, 2], "lines": ["- a", "+ a"]}
                        ],
                    }
                }
            },
            {"files": {"a": {"l": {"1": {"c": 1}}}}},
            None,
            False,
        ),  # lines not tracked`
    ],
)
def test_does_diff_adjust_tracked_lines(diff, future, future_diff, res):
    v3 = v2_to_v3({"files": {"a": {"l": {"1": {"c": 1}, "2": {"c": 1}}}}})
    r = Report(files=v3["files"])
    r.sessions = v3["sessions"]
    r._totals = v3["totals"]
    r._chunks = v3["chunks"]
    r._path_filter = None
    r._line_modifier = None
    if future:
        futuree = v2_to_v3(future)
    else:
        futuree = v2_to_v3({"files": {"z": {}}})

    future_r = Report(files=futuree["files"])
    future_r.sessions = futuree["sessions"]
    future_r._totals = futuree["totals"]
    future_r._chunks = futuree["chunks"]
    future_r._path_filter = None
    future_r._line_modifier = None

    assert r.does_diff_adjust_tracked_lines(diff, future_r, future_diff) == res


@pytest.mark.unit
def test_calculate_diff():
    v3 = {
        "files": {"a": [0, None], "d": [1, None]},
        "sessions": {},
        "totals": {},
        "chunks": [
            "\n[1, null, null, null]\n[0, null, null, null]",
            "\n[1, null, null, null]\n[0, null, null, null]",
        ],
    }
    r = Report(**v3)
    diff = {
        "files": {
            "a": {
                "type": "new",
                "segments": [{"header": list("1313"), "lines": list("---+++")}],
            },
            "b": {"type": "deleted"},
            "c": {"type": "modified"},
            "d": {
                "type": "modified",
                "segments": [
                    {"header": ["10", "3", "10", "3"], "lines": list("---+++")}
                ],
            },
        }
    }
    res = r.calculate_diff(diff)
    expected_result = {
        "files": {
            "a": ReportTotals(
                files=0, lines=2, hits=1, misses=1, partials=0, coverage="50.00000"
            ),
            "d": ReportTotals(
                files=0, lines=0, hits=0, misses=0, partials=0, coverage=None
            ),
        },
        "general": ReportTotals(
            files=2,
            lines=2,
            hits=1,
            misses=1,
            partials=0,
            coverage="50.00000",
            branches=0,
            methods=0,
            messages=0,
            sessions=0,
            complexity=0,
            complexity_total=0,
            diff=0,
        ),
    }
    assert res["files"] == expected_result["files"]
    assert res == expected_result


@pytest.mark.unit
def test_apply_diff():
    v3 = {
        "files": {"a": [0, None], "d": [1, None]},
        "sessions": {},
        "totals": {},
        "chunks": [
            "\n[1, null, null, null]\n[0, null, null, null]",
            "\n[1, null, null, null]\n[0, null, null, null]",
        ],
    }
    r = Report(**v3)
    diff = {
        "files": {
            "a": {
                "type": "new",
                "segments": [{"header": list("1313"), "lines": list("---+++")}],
            },
            "b": {"type": "deleted"},
            "c": {"type": "modified"},
            "d": {
                "type": "modified",
                "segments": [
                    {"header": ["10", "3", "10", "3"], "lines": list("---+++")}
                ],
            },
        }
    }
    assert r.apply_diff(None) is None
    assert r.apply_diff({}) is None
    res = r.apply_diff(diff)
    assert res == diff["totals"]
    assert diff["totals"].coverage == "50.00000"


@pytest.mark.unit
def test_apply_diff_no_diff():
    v3 = {
        "files": {"a": [0, None], "d": [1, None]},
        "sessions": {},
        "totals": {},
        "chunks": [
            "\n[1, null, null, null]\n[0, null, null, null]",
            "\n[1, null, null, null]\n[0, null, null, null]",
        ],
    }
    r = Report(**v3)
    diff = {"files": {}}
    res = r.apply_diff(diff)
    assert res is None
    assert diff == {"files": {}}


@pytest.mark.unit
def test_apply_diff_no_append(mocker):
    v3 = v2_to_v3({"files": {"a": {"l": {"1": {"c": 1}, "2": {"c": 0}}}}})
    r = Report(files=v3["files"])
    r.sessions = v3["sessions"]
    r._totals = v3["totals"]
    r._chunks = v3["chunks"]
    r._path_filter = None
    r._line_modifier = None
    diff = {
        "files": {
            "a": {
                "type": "new",
                "segments": [{"header": list("1313"), "lines": list("---+++")}],
            },
            "b": {"type": "deleted"},
            "c": {"type": "modified"},
        }
    }
    res = r.apply_diff(diff, _save=False)
    assert "totals" not in diff
    assert "totals" not in diff["files"]["a"]
    assert "totals" not in diff["files"]["c"]
    assert res.coverage == "50.00000"


@pytest.mark.unit
def test_add_session(mocker):
    r = Report()
    s = Session(5)
    r._files = {"file.py": [0, ReportTotals(0)]}
    r._chunks = None
    r._totals = ReportTotals(0)
    r.sessions = {}
    assert r.totals.sessions == 0
    assert r.sessions == {}
    assert r.add_session(s) == (0, s)
    assert r.totals.sessions == 1
    assert r.sessions == {0: s}


@pytest.mark.unit
@pytest.mark.parametrize(
    "files, chunks, params, flare",
    [
        (
            {"py.py": [0, ReportTotals(1)]},
            "null\n[1]\n[1]\n[1]\n<<<<< end_of_chunk >>>>>\nnull\n[1]\n[1]\n[1]".split(
                END_OF_CHUNK
            ),
            {
                "color": lambda cov: "purple"
                if cov is None
                else "#e1e1e1"
                if cov == 0
                else "green"
                if cov > 0
                else "red"
            },
            [
                {
                    "name": "",
                    "coverage": 100,
                    "color": "green",
                    "_class": None,
                    "lines": 0,
                    "children": [
                        {
                            "color": "#e1e1e1",
                            "_class": None,
                            "lines": 0,
                            "name": "py.py",
                            "coverage": 0,
                        }
                    ],
                }
            ],
        ),
        (
            {"py.py": [0, ReportTotals(1)]},
            None,
            {"changes": {}},
            [
                {
                    "name": "",
                    "coverage": 100,
                    "color": "green",
                    "_class": None,
                    "lines": 0,
                    "children": [
                        {
                            "color": "#e1e1e1",
                            "_class": None,
                            "lines": 0,
                            "name": "py.py",
                            "coverage": 0,
                        }
                    ],
                }
            ],
        ),
    ],
)
def test_flare(files, chunks, params, flare):
    r = Report(files=files)
    r._chunks = chunks
    r._path_filter = None
    r._line_modifier = None
    assert r.flare(**params) == flare


@pytest.mark.unit
def test_filter_exception(mocker):
    Report._filter_cache = (None, None)
    with pytest.raises(Exception) as e_info:
        Report().filter(paths="str")
    assert str(e_info.value) == "expecting list for argument paths got <class 'str'>"


@pytest.mark.unit
@pytest.mark.parametrize(
    "chunk, res",
    [
        (None, "null"),
        (ReportFile(name="name.ply"), "{}\n"),
        (
            [ReportLine.create(2), ReportLine.create(1)],
            "[[2,null,null,null,null,null],[1,null,null,null,null,null]]",
        ),
    ],
)
def test_encode_chunk(chunk, res):
    assert _encode_chunk(chunk) == res


@pytest.mark.unit
def test_delete_session():
    chunks = "\n".join(
        [
            "{}",
            "[1, null, [[0, 1], [1, 0]]]",
            "",
            "",
            "[0, null, [[0, 0], [1, 0]]]",
            "[1, null, [[0, 1], [1, 1]]]",
            "[1, null, [[0, 0], [1, 1]]]",
            "",
            "",
            '[1, null, [[0, 1], [1, "1/2"]]]',
            '[1, null, [[0, "1/2"], [1, 1]]]',
            "",
            "",
            "[1, null, [[0, 1]]]",
            "[1, null, [[1, 1]]]",
            '["1/2", null, [[0, "1/2"], [1, 0]]]',
            '["1/2", null, [[0, 0], [1, "1/2"]]]',
        ]
    )
    report_file = ReportFile(name="file.py", lines=chunks)
    assert report_file._lines == chunks.split("\n")[1:]
    assert report_file.totals == ReportTotals(
        files=0,
        lines=10,
        hits=7,
        misses=1,
        partials=2,
        coverage="70.00000",
        branches=0,
        methods=0,
        messages=0,
        sessions=0,
        complexity=0,
        complexity_total=0,
        diff=0,
    )
    report_file.delete_session(1)
    expected_result = [
        (1, ReportLine.create(coverage=1, sessions=[LineSession(0, 1)])),
        (4, ReportLine.create(coverage=0, sessions=[LineSession(0, 0)])),
        (5, ReportLine.create(coverage=1, sessions=[LineSession(0, 1)])),
        (6, ReportLine.create(coverage=0, sessions=[LineSession(0, 0)])),
        (9, ReportLine.create(coverage=1, sessions=[LineSession(0, 1)])),
        (10, ReportLine.create(coverage="1/2", sessions=[LineSession(0, "1/2")])),
        (13, ReportLine.create(coverage=1, sessions=[LineSession(0, 1)])),
        (15, ReportLine.create(coverage="1/2", sessions=[LineSession(0, "1/2")])),
        (16, ReportLine.create(coverage=0, sessions=[LineSession(0, 0)])),
    ]
    assert list(report_file.lines) == expected_result
    assert report_file.get(1) == ReportLine.create(
        coverage=1, sessions=[LineSession(0, 1)]
    )
    assert report_file.get(13) == ReportLine.create(
        coverage=1, sessions=[LineSession(0, 1)]
    )
    assert report_file.get(14) is None
    assert report_file.totals == ReportTotals(
        files=0,
        lines=9,
        hits=4,
        misses=3,
        partials=2,
        coverage="44.44444",
        branches=0,
        methods=0,
        messages=0,
        sessions=0,
        complexity=0,
        complexity_total=0,
        diff=0,
    )


@pytest.mark.unit
def test_get_flag_names(sample_report):
    assert sample_report.get_flag_names() == ["complex", "simple"]


@pytest.mark.unit
def test_get_flag_names_no_sessions():
    assert Report().get_flag_names() == []


@pytest.mark.unit
def test_get_flag_names_sessions_no_flags():
    s = Session()
    r = Report()
    r.add_session(s)
    assert r.get_flag_names() == []


@pytest.mark.unit
def test_repack(sample_report):
    f = ReportFile("hahafile.txt")
    f.append(1, ReportLine.create(1))
    sample_report.append(f)
    del sample_report["file_2.go"]
    del sample_report["hahafile.txt"]
    old_totals = sample_report.totals
    assert len(sample_report._chunks) == 4
    assert len(sample_report._files) == 2
    assert sorted(k.file_index for k in sample_report._files.values()) == [0, 2]
    old_line_count = sum(len(list(file.lines)) for file in sample_report)
    sample_report.repack()
    sample_report._totals = None
    assert sample_report.totals == old_totals
    assert sorted(sample_report.files) == ["file_1.go", "location/file_1.py"]
    assert len(sample_report._chunks) == len(sample_report._files)
    assert sorted(k.file_index for k in sample_report._files.values()) == [0, 1]
    assert old_line_count == sum(len(list(file.lines)) for file in sample_report)


@pytest.mark.unit
def test_repack_bad_data(sample_report):
    f = ReportFile("hahafile.txt")
    f.append(1, ReportLine.create(1))
    sample_report.append(f)
    assert len(sample_report._chunks) == 4
    assert len(sample_report._files) == 4
    assert sorted(k.file_index for k in sample_report._files.values()) == [0, 1, 2, 3]
    del sample_report._files["hahafile.txt"]
    sample_report._chunks[0] = None
    assert len(sample_report._chunks) == 4
    assert len(sample_report._files) == 3
    assert sorted(k.file_index for k in sample_report._files.values()) == [0, 1, 2]
    old_totals = sample_report.totals
    old_line_count = sum(len(list(file.lines)) for file in sample_report)
    sample_report.repack()
    sample_report._totals = None
    assert sample_report.totals == old_totals
    assert sorted(sample_report.files) == [
        "file_1.go",
        "file_2.go",
        "location/file_1.py",
    ]
    assert len(sample_report._chunks) == 4
    assert len(sample_report._files) == 3
    assert sorted(k.file_index for k in sample_report._files.values()) == [0, 1, 2]
    assert old_line_count == sum(len(list(file.lines)) for file in sample_report)


@pytest.mark.unit
def test_repack_no_change(sample_report):
    assert len(sample_report._chunks) == len(sample_report._files)
    sample_report.repack()
    assert len(sample_report._chunks) == len(sample_report._files)


@pytest.mark.unit
def test_shift_lines_by_diff():
    r = ReportFile("filename")
    r._lines = [ReportLine.create(n) for n in range(8)]
    report = Report(sessions={0: Session()})
    report.append(r)
    assert list(r.lines) == [
        (
            1,
            ReportLine(
                coverage=0,
                type=None,
                sessions=None,
                messages=None,
                complexity=None,
                datapoints=None,
            ),
        ),
        (
            2,
            ReportLine(
                coverage=1,
                type=None,
                sessions=None,
                messages=None,
                complexity=None,
                datapoints=None,
            ),
        ),
        (
            3,
            ReportLine(
                coverage=2,
                type=None,
                sessions=None,
                messages=None,
                complexity=None,
                datapoints=None,
            ),
        ),
        (
            4,
            ReportLine(
                coverage=3,
                type=None,
                sessions=None,
                messages=None,
                complexity=None,
                datapoints=None,
            ),
        ),
        (
            5,
            ReportLine(
                coverage=4,
                type=None,
                sessions=None,
                messages=None,
                complexity=None,
                datapoints=None,
            ),
        ),
        (
            6,
            ReportLine(
                coverage=5,
                type=None,
                sessions=None,
                messages=None,
                complexity=None,
                datapoints=None,
            ),
        ),
        (
            7,
            ReportLine(
                coverage=6,
                type=None,
                sessions=None,
                messages=None,
                complexity=None,
                datapoints=None,
            ),
        ),
        (
            8,
            ReportLine(
                coverage=7,
                type=None,
                sessions=None,
                messages=None,
                complexity=None,
                datapoints=None,
            ),
        ),
    ]
    assert report.totals == ReportTotals(
        files=1,
        lines=8,
        hits=7,
        misses=1,
        partials=0,
        coverage="87.50000",
        branches=0,
        methods=0,
        messages=0,
        sessions=1,
        complexity=0,
        complexity_total=0,
        diff=0,
    )
    report.shift_lines_by_diff(
        {
            "files": {
                "filename": {
                    "type": "modified",
                    "segments": [
                        {
                            # [-, -, POS_to_start, new_lines_added]
                            "header": [1, 1, 1, 1],
                            "lines": ["- afefe", "+ fefe", "="],
                        },
                        {
                            # [-, -, POS_to_start, new_lines_added]
                            "header": [5, 3, 5, 2],
                            "lines": ["- ", "- ", "- ", "+ ", "+ ", " ="],
                        },
                    ],
                }
            }
        }
    )
    assert report.files == ["filename"]
    assert list(report.get("filename").lines) == [
        (
            2,
            ReportLine(
                coverage=1,
                type=None,
                sessions=None,
                messages=None,
                complexity=None,
                datapoints=None,
            ),
        ),
        (
            3,
            ReportLine(
                coverage=2,
                type=None,
                sessions=None,
                messages=None,
                complexity=None,
                datapoints=None,
            ),
        ),
        (
            4,
            ReportLine(
                coverage=3,
                type=None,
                sessions=None,
                messages=None,
                complexity=None,
                datapoints=None,
            ),
        ),
        (
            7,
            ReportLine(
                coverage=7,
                type=None,
                sessions=None,
                messages=None,
                complexity=None,
                datapoints=None,
            ),
        ),
    ]
    assert report._files == {
        "filename": ReportFileSummary(
            file_index=0,
            file_totals=ReportTotals(
                files=0,
                lines=4,
                hits=4,
                misses=0,
                partials=0,
                coverage="100",
                branches=0,
                methods=0,
                messages=0,
                sessions=0,
                complexity=0,
                complexity_total=0,
                diff=0,
            ),
            diff_totals=None,
        )
    }
