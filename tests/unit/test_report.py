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
    ReportFileSummary,
    ReportHeader,
    ReportLine,
    ReportTotals,
)
from shared.utils.sessions import Session


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


def test_files():
    r = Report(files={"py.py": [0, ReportTotals(1)]})
    assert r.files == ["py.py"]


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
def test_encode_chunk():
    assert _encode_chunk(None) == b"null"
    assert _encode_chunk(ReportFile(name="name.ply")) == b'{"present_sessions":[]}\n'
    assert (
        _encode_chunk([ReportLine.create(2), ReportLine.create(1)])
        == b"[[2,null,null,null,null,null],[1,null,null,null,null,null]]"
    )


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
    report_file = EditableReportFile(name="file.py", lines=chunks)
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
    report_file.delete_multiple_sessions({1})
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
    r = ReportFile("filename", lines=[ReportLine.create(n) for n in range(8)])
    report = Report(sessions={0: Session()})
    report.append(r)
    assert list(r.lines) == [
        (1, ReportLine.create(0)),
        (2, ReportLine.create(1)),
        (3, ReportLine.create(2)),
        (4, ReportLine.create(3)),
        (5, ReportLine.create(4)),
        (6, ReportLine.create(5)),
        (7, ReportLine.create(6)),
        (8, ReportLine.create(7)),
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
        (2, ReportLine.create(1)),
        (3, ReportLine.create(2)),
        (4, ReportLine.create(3)),
        (7, ReportLine.create(7)),
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
