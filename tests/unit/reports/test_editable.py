from pathlib import Path
from json import loads
import dataclasses
from fractions import Fraction
import pprint

import pytest

from covreports.reports.types import ReportLine, LineSession, ReportTotals
from covreports.reports.resources import ReportFileSummary, Session
from covreports.utils.merge import merge_coverage
from covreports.utils.sessions import SessionType
from covreports.reports.editable import (
    EditableReportFile,
    EditableReport,
)

current_file = Path(__file__)


def test_merge_coverage():
    assert merge_coverage(0.5, Fraction(3, 4)) == Fraction(3, 4)
    assert merge_coverage(2, Fraction(3, 4)) == 2


class TestEditableReportHelpers(object):
    def test_line_without_session(self):
        line = ReportLine(1, None, [LineSession(1, 0), LineSession(0, 1)])
        assert EditableReportFile.line_without_session(line, 1) == ReportLine(
            1, None, [LineSession(0, 1)]
        )
        assert EditableReportFile.line_without_session(line, 0) == ReportLine(
            0, None, [LineSession(1, 0)]
        )
        assert (
            EditableReportFile.line_without_session(
                EditableReportFile.line_without_session(line, 0), 1
            )
            == ""
        )


class TestEditableReportFile(object):
    def test_init(self):
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
        expected_result = [
            ReportLine(coverage=1, sessions=[LineSession(0, 1), LineSession(1, 0)]),
            "",
            "",
            ReportLine(coverage=0, sessions=[LineSession(0, 0), LineSession(1, 0)]),
            ReportLine(coverage=1, sessions=[LineSession(0, 1), LineSession(1, 1)]),
            ReportLine(coverage=1, sessions=[LineSession(0, 0), LineSession(1, 1)]),
            "",
            "",
            ReportLine(coverage=1, sessions=[LineSession(0, 1), LineSession(1, "1/2")]),
            ReportLine(coverage=1, sessions=[LineSession(0, "1/2"), LineSession(1, 1)]),
            "",
            "",
            ReportLine(coverage=1, sessions=[LineSession(0, 1)]),
            ReportLine(coverage=1, sessions=[LineSession(1, 1)]),
            ReportLine(
                coverage="1/2", sessions=[LineSession(0, "1/2"), LineSession(1, 0)]
            ),
            ReportLine(
                coverage="1/2", sessions=[LineSession(0, 0), LineSession(1, "1/2")]
            ),
        ]
        assert report_file._lines == expected_result

    def test_delete_session(self):
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
        original_lines = [
            ReportLine(coverage=1, sessions=[LineSession(0, 1), LineSession(1, 0)]),
            "",
            "",
            ReportLine(coverage=0, sessions=[LineSession(0, 0), LineSession(1, 0)]),
            ReportLine(coverage=1, sessions=[LineSession(0, 1), LineSession(1, 1)]),
            ReportLine(coverage=1, sessions=[LineSession(0, 0), LineSession(1, 1)]),
            "",
            "",
            ReportLine(coverage=1, sessions=[LineSession(0, 1), LineSession(1, "1/2")]),
            ReportLine(coverage=1, sessions=[LineSession(0, "1/2"), LineSession(1, 1)]),
            "",
            "",
            ReportLine(coverage=1, sessions=[LineSession(0, 1)]),
            ReportLine(coverage=1, sessions=[LineSession(1, 1)]),
            ReportLine(
                coverage="1/2", sessions=[LineSession(0, "1/2"), LineSession(1, 0)]
            ),
            ReportLine(
                coverage="1/2", sessions=[LineSession(0, 0), LineSession(1, "1/2")]
            ),
        ]
        assert report_file._lines == original_lines
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
            ReportLine(coverage=1, sessions=[LineSession(0, 1)]),
            "",
            "",
            ReportLine(coverage=0, sessions=[LineSession(0, 0)]),
            ReportLine(coverage=1, sessions=[LineSession(0, 1)]),
            ReportLine(coverage=0, sessions=[LineSession(0, 0)]),
            "",
            "",
            ReportLine(coverage=1, sessions=[LineSession(0, 1)]),
            ReportLine(coverage="1/2", sessions=[LineSession(0, "1/2")]),
            "",
            "",
            ReportLine(coverage=1, sessions=[LineSession(0, 1)]),
            "",
            ReportLine(coverage="1/2", sessions=[LineSession(0, "1/2")]),
            ReportLine(coverage=0, sessions=[LineSession(0, 0)]),
        ]
        assert report_file._lines == expected_result
        assert report_file.get(1) == ReportLine(
            coverage=1, sessions=[LineSession(0, 1)]
        )
        assert report_file.get(13) == ReportLine(
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


@pytest.fixture
def sample_report():
    report = EditableReport()
    first_file = EditableReportFile("file_1.go")
    first_file.append(
        1,
        ReportLine(
            coverage=1,
            sessions=[LineSession(0, 1), LineSession(1, 1), LineSession(2, 1)],
            complexity=(10, 2),
        ),
    )
    first_file.append(
        2,
        ReportLine(
            coverage=1,
            sessions=[LineSession(0, 1), LineSession(1, "1/2"), LineSession(2, 1)],
            complexity=(10, 2),
        ),
    )
    first_file.append(
        3, ReportLine(coverage=1, sessions=[LineSession(0, 1)], complexity=(10, 2),),
    )
    first_file.append(
        4, ReportLine(coverage=1, sessions=[LineSession(1, 1)], complexity=(10, 2),),
    )
    first_file.append(
        5, ReportLine(coverage=1, sessions=[LineSession(2, 1)], complexity=(10, 2),),
    )
    first_file.append(
        6,
        ReportLine(
            coverage=1,
            sessions=[LineSession(0, 1), LineSession(1, 1)],
            complexity=(10, 2),
        ),
    )
    first_file.append(
        7,
        ReportLine(
            coverage=1,
            sessions=[LineSession(1, 1), LineSession(2, 1)],
            complexity=(10, 2),
        ),
    )
    first_file.append(
        8,
        ReportLine(
            coverage=1,
            sessions=[LineSession(2, 1), LineSession(0, 1)],
            complexity=(10, 2),
        ),
    )
    second_file = EditableReportFile("file_2.py")
    second_file.append(
        12,
        ReportLine(
            coverage=1,
            sessions=[LineSession(0, 1), LineSession(1, "1/2"), LineSession(2, 0)],
        ),
    )
    second_file.append(
        51,
        ReportLine(
            coverage="1/2",
            type="b",
            sessions=[LineSession(0, "1/3"), LineSession(1, "1/2")],
        ),
    )
    single_session_file = EditableReportFile("single_session_file.c")
    single_session_file.append(
        101, ReportLine(coverage="1/2", sessions=[LineSession(1, "1/2")],),
    )
    single_session_file.append(
        110, ReportLine(coverage=1, sessions=[LineSession(1, 1)],),
    )
    single_session_file.append(
        111, ReportLine(coverage=0, sessions=[LineSession(1, 0)],),
    )
    report.append(first_file)
    report.append(second_file)
    report.append(single_session_file)
    report.add_session(Session(id=0, flags=["unit"]))
    report.add_session(
        Session(id=1, flags=["integration"], session_type=SessionType.carriedforward)
    )
    report.add_session(Session(id=2, flags=None))
    return report


class TestEditableReport(object):
    def convert_report_to_better_readable(self, report):
        totals_dict, report_dict = report.to_database()
        report_dict = loads(report_dict)
        archive_dict = {}
        for filename in report.files:
            file_report = report.get(filename)
            lines = []
            for line_number, line in file_report.lines:
                (
                    coverage,
                    line_type,
                    sessions,
                    messages,
                    complexity,
                ) = dataclasses.astuple(line)
                sessions = [list(s) for s in sessions]
                lines.append(
                    (line_number, coverage, line_type, sessions, messages, complexity)
                )
            archive_dict[filename] = lines
        return {"totals": totals_dict, "report": report_dict, "archive": archive_dict}

    def test_init(self):
        with open(current_file.parent / "samples" / "chunks_01.txt", "r") as f:
            chunks = f.read()
        files_dict = {
            "awesome/__init__.py": [
                2,
                [0, 10, 8, 2, 0, "80.00000", 0, 0, 0, 0, 0, 0, 0],
                [[0, 10, 8, 2, 0, "80.00000", 0, 0, 0, 0, 0, 0, 0]],
                [0, 2, 1, 1, 0, "50.00000", 0, 0, 0, 0, 0, 0, 0],
            ],
            "tests/__init__.py": [
                0,
                [0, 3, 2, 1, 0, "66.66667", 0, 0, 0, 0, 0, 0, 0],
                [[0, 3, 2, 1, 0, "66.66667", 0, 0, 0, 0, 0, 0, 0]],
                None,
            ],
            "tests/test_sample.py": [
                1,
                [0, 7, 7, 0, 0, "100", 0, 0, 0, 0, 0, 0, 0],
                [[0, 7, 7, 0, 0, "100", 0, 0, 0, 0, 0, 0, 0]],
                None,
            ],
        }
        sessions_dict = {
            "0": {
                "N": None,
                "a": "v4/raw/2019-01-10/4434BC2A2EC4FCA57F77B473D83F928C/abf6d4df662c47e32460020ab14abf9303581429/9ccc55a1-8b41-4bb1-a946-ee7a33a7fb56.txt",
                "c": None,
                "d": 1547084427,
                "e": None,
                "f": ["unit"],
                "j": None,
                "n": None,
                "p": None,
                "t": [3, 20, 17, 3, 0, "85.00000", 0, 0, 0, 0, 0, 0, 0],
                "": None,
            }
        }
        report = EditableReport(chunks=chunks, files=files_dict, sessions=sessions_dict)
        assert report._files == {
            "awesome/__init__.py": ReportFileSummary(
                2,
                [0, 10, 8, 2, 0, "80.00000", 0, 0, 0, 0, 0, 0, 0],
                [[0, 10, 8, 2, 0, "80.00000", 0, 0, 0, 0, 0, 0, 0]],
                [0, 2, 1, 1, 0, "50.00000", 0, 0, 0, 0, 0, 0, 0],
            ),
            "tests/__init__.py": ReportFileSummary(
                0,
                [0, 3, 2, 1, 0, "66.66667", 0, 0, 0, 0, 0, 0, 0],
                [[0, 3, 2, 1, 0, "66.66667", 0, 0, 0, 0, 0, 0, 0]],
                None,
            ),
            "tests/test_sample.py": ReportFileSummary(
                1,
                [0, 7, 7, 0, 0, "100", 0, 0, 0, 0, 0, 0, 0],
                [[0, 7, 7, 0, 0, "100", 0, 0, 0, 0, 0, 0, 0]],
                None,
            ),
        }
        assert all(isinstance(x, EditableReportFile) for x in report._chunks)

    def test_delete_session(self, sample_report):
        report = sample_report

        pprint.pprint(self.convert_report_to_better_readable(report))
        assert self.convert_report_to_better_readable(report) == {
            "archive": {
                "file_1.go": [
                    (
                        1,
                        1,
                        None,
                        [
                            [0, 1, None, None, None],
                            [1, 1, None, None, None],
                            [2, 1, None, None, None],
                        ],
                        None,
                        (10, 2),
                    ),
                    (
                        2,
                        1,
                        None,
                        [
                            [0, 1, None, None, None],
                            [1, "1/2", None, None, None],
                            [2, 1, None, None, None],
                        ],
                        None,
                        (10, 2),
                    ),
                    (3, 1, None, [[0, 1, None, None, None]], None, (10, 2)),
                    (4, 1, None, [[1, 1, None, None, None]], None, (10, 2)),
                    (5, 1, None, [[2, 1, None, None, None]], None, (10, 2)),
                    (
                        6,
                        1,
                        None,
                        [[0, 1, None, None, None], [1, 1, None, None, None]],
                        None,
                        (10, 2),
                    ),
                    (
                        7,
                        1,
                        None,
                        [[1, 1, None, None, None], [2, 1, None, None, None]],
                        None,
                        (10, 2),
                    ),
                    (
                        8,
                        1,
                        None,
                        [[2, 1, None, None, None], [0, 1, None, None, None]],
                        None,
                        (10, 2),
                    ),
                ],
                "file_2.py": [
                    (
                        12,
                        1,
                        None,
                        [
                            [0, 1, None, None, None],
                            [1, "1/2", None, None, None],
                            [2, 0, None, None, None],
                        ],
                        None,
                        None,
                    ),
                    (
                        51,
                        "1/2",
                        "b",
                        [[0, "1/3", None, None, None], [1, "1/2", None, None, None]],
                        None,
                        None,
                    ),
                ],
                "single_session_file.c": [
                    (101, "1/2", None, [[1, "1/2", None, None, None]], None, None),
                    (110, 1, None, [[1, 1, None, None, None]], None, None),
                    (111, 0, None, [[1, 0, None, None, None]], None, None),
                ],
            },
            "report": {
                "files": {
                    "file_1.go": [
                        0,
                        [0, 8, 8, 0, 0, "100", 0, 0, 0, 0, 80, 16, 0],
                        [[0, 8, 8, 0, 0, "100", 0, 0, 0, 0, 80, 16, 0]],
                        None,
                    ],
                    "file_2.py": [
                        1,
                        [0, 2, 1, 0, 1, "50.00000", 1, 0, 0, 0, 0, 0, 0],
                        [[0, 2, 1, 0, 1, "50.00000", 1, 0, 0, 0, 0, 0, 0]],
                        None,
                    ],
                    "single_session_file.c": [
                        2,
                        [0, 3, 1, 1, 1, "33.33333", 0, 0, 0, 0, 0, 0, 0],
                        [[0, 3, 1, 1, 1, "33.33333", 0, 0, 0, 0, 0, 0, 0]],
                        None,
                    ],
                },
                "sessions": {
                    "0": {
                        "N": None,
                        "a": None,
                        "c": None,
                        "d": None,
                        "e": None,
                        "f": ["unit"],
                        "j": None,
                        "n": None,
                        "p": None,
                        "st": "uploaded",
                        "se": {},
                        "t": None,
                        "u": None,
                    },
                    "1": {
                        "N": None,
                        "a": None,
                        "c": None,
                        "d": None,
                        "e": None,
                        "f": ["integration"],
                        "j": None,
                        "n": None,
                        "p": None,
                        "st": "carriedforward",
                        "se": {},
                        "t": None,
                        "u": None,
                    },
                    "2": {
                        "N": None,
                        "a": None,
                        "c": None,
                        "d": None,
                        "e": None,
                        "f": None,
                        "j": None,
                        "n": None,
                        "p": None,
                        "st": "uploaded",
                        "se": {},
                        "t": None,
                        "u": None,
                    },
                },
            },
            "totals": {
                "C": 80,
                "M": 0,
                "N": 16,
                "b": 1,
                "c": "76.92308",
                "d": 0,
                "diff": None,
                "f": 3,
                "h": 10,
                "m": 1,
                "n": 13,
                "p": 2,
                "s": 3,
            },
        }
        report.delete_session(1)
        expected_result = {
            "archive": {
                "file_1.go": [
                    (
                        1,
                        1,
                        None,
                        [[0, 1, None, None, None], [2, 1, None, None, None]],
                        None,
                        (10, 2),
                    ),
                    (
                        2,
                        1,
                        None,
                        [[0, 1, None, None, None], [2, 1, None, None, None]],
                        None,
                        (10, 2),
                    ),
                    (3, 1, None, [[0, 1, None, None, None]], None, (10, 2)),
                    (5, 1, None, [[2, 1, None, None, None]], None, (10, 2)),
                    (6, 1, None, [[0, 1, None, None, None]], None, (10, 2)),
                    (7, 1, None, [[2, 1, None, None, None]], None, (10, 2)),
                    (
                        8,
                        1,
                        None,
                        [[2, 1, None, None, None], [0, 1, None, None, None]],
                        None,
                        (10, 2),
                    ),
                ],
                "file_2.py": [
                    (
                        12,
                        1,
                        None,
                        [[0, 1, None, None, None], [2, 0, None, None, None]],
                        None,
                        None,
                    ),
                    (51, "1/3", "b", [[0, "1/3", None, None, None]], None, None),
                ],
            },
            "report": {
                "files": {
                    "file_1.go": [
                        0,
                        [0, 7, 7, 0, 0, "100", 0, 0, 0, 0, 70, 14, 0],
                        [[0, 8, 8, 0, 0, "100", 0, 0, 0, 0, 80, 16, 0]],
                        None,
                    ],
                    "file_2.py": [
                        1,
                        [0, 2, 1, 0, 1, "50.00000", 1, 0, 0, 0, 0, 0, 0],
                        [[0, 2, 1, 0, 1, "50.00000", 1, 0, 0, 0, 0, 0, 0]],
                        None,
                    ],
                },
                "sessions": {
                    "0": {
                        "N": None,
                        "a": None,
                        "c": None,
                        "d": None,
                        "e": None,
                        "f": ["unit"],
                        "j": None,
                        "n": None,
                        "p": None,
                        "st": "uploaded",
                        "se": {},
                        "t": None,
                        "u": None,
                    },
                    "2": {
                        "N": None,
                        "a": None,
                        "c": None,
                        "d": None,
                        "e": None,
                        "f": None,
                        "j": None,
                        "n": None,
                        "p": None,
                        "st": "uploaded",
                        "se": {},
                        "t": None,
                        "u": None,
                    },
                },
            },
            "totals": {
                "C": 70,
                "M": 0,
                "N": 14,
                "b": 1,
                "c": "88.88889",
                "d": 0,
                "diff": None,
                "f": 2,
                "h": 8,
                "m": 0,
                "n": 9,
                "p": 1,
                "s": 2,
            },
        }
        res = self.convert_report_to_better_readable(report)
        assert res["archive"] == expected_result["archive"]
        assert res["report"] == expected_result["report"]
        assert res["totals"] == expected_result["totals"]
        assert res == expected_result
        report.delete_session(0)
        report.delete_session(2)
        assert self.convert_report_to_better_readable(report) == {
            "archive": {},
            "report": {"files": {}, "sessions": {}},
            "totals": {
                "C": 0,
                "M": 0,
                "N": 0,
                "b": 0,
                "c": 0,
                "d": 0,
                "diff": None,
                "f": 0,
                "h": 0,
                "m": 0,
                "n": 0,
                "p": 0,
                "s": 0,
            },
        }

    def test_add_conflicting_session(self, sample_report):
        report = sample_report
        import pprint

        # pprint.pprint(self.convert_report_to_better_readable(report))
        assert self.convert_report_to_better_readable(report) == {
            "archive": {
                "file_1.go": [
                    (
                        1,
                        1,
                        None,
                        [
                            [0, 1, None, None, None],
                            [1, 1, None, None, None],
                            [2, 1, None, None, None],
                        ],
                        None,
                        (10, 2),
                    ),
                    (
                        2,
                        1,
                        None,
                        [
                            [0, 1, None, None, None],
                            [1, "1/2", None, None, None],
                            [2, 1, None, None, None],
                        ],
                        None,
                        (10, 2),
                    ),
                    (3, 1, None, [[0, 1, None, None, None]], None, (10, 2)),
                    (4, 1, None, [[1, 1, None, None, None]], None, (10, 2)),
                    (5, 1, None, [[2, 1, None, None, None]], None, (10, 2)),
                    (
                        6,
                        1,
                        None,
                        [[0, 1, None, None, None], [1, 1, None, None, None]],
                        None,
                        (10, 2),
                    ),
                    (
                        7,
                        1,
                        None,
                        [[1, 1, None, None, None], [2, 1, None, None, None]],
                        None,
                        (10, 2),
                    ),
                    (
                        8,
                        1,
                        None,
                        [[2, 1, None, None, None], [0, 1, None, None, None]],
                        None,
                        (10, 2),
                    ),
                ],
                "file_2.py": [
                    (
                        12,
                        1,
                        None,
                        [
                            [0, 1, None, None, None],
                            [1, "1/2", None, None, None],
                            [2, 0, None, None, None],
                        ],
                        None,
                        None,
                    ),
                    (
                        51,
                        "1/2",
                        "b",
                        [[0, "1/3", None, None, None], [1, "1/2", None, None, None]],
                        None,
                        None,
                    ),
                ],
                "single_session_file.c": [
                    (101, "1/2", None, [[1, "1/2", None, None, None]], None, None),
                    (110, 1, None, [[1, 1, None, None, None]], None, None),
                    (111, 0, None, [[1, 0, None, None, None]], None, None),
                ],
            },
            "report": {
                "files": {
                    "file_1.go": [
                        0,
                        [0, 8, 8, 0, 0, "100", 0, 0, 0, 0, 80, 16, 0],
                        [[0, 8, 8, 0, 0, "100", 0, 0, 0, 0, 80, 16, 0]],
                        None,
                    ],
                    "file_2.py": [
                        1,
                        [0, 2, 1, 0, 1, "50.00000", 1, 0, 0, 0, 0, 0, 0],
                        [[0, 2, 1, 0, 1, "50.00000", 1, 0, 0, 0, 0, 0, 0]],
                        None,
                    ],
                    "single_session_file.c": [
                        2,
                        [0, 3, 1, 1, 1, "33.33333", 0, 0, 0, 0, 0, 0, 0],
                        [[0, 3, 1, 1, 1, "33.33333", 0, 0, 0, 0, 0, 0, 0]],
                        None,
                    ],
                },
                "sessions": {
                    "0": {
                        "N": None,
                        "a": None,
                        "c": None,
                        "d": None,
                        "e": None,
                        "f": ["unit"],
                        "j": None,
                        "n": None,
                        "p": None,
                        "st": "uploaded",
                        "se": {},
                        "t": None,
                        "u": None,
                    },
                    "1": {
                        "N": None,
                        "a": None,
                        "c": None,
                        "d": None,
                        "e": None,
                        "f": ["integration"],
                        "j": None,
                        "n": None,
                        "p": None,
                        "st": "carriedforward",
                        "se": {},
                        "t": None,
                        "u": None,
                    },
                    "2": {
                        "N": None,
                        "a": None,
                        "c": None,
                        "d": None,
                        "e": None,
                        "f": None,
                        "j": None,
                        "n": None,
                        "p": None,
                        "st": "uploaded",
                        "se": {},
                        "t": None,
                        "u": None,
                    },
                },
            },
            "totals": {
                "C": 80,
                "M": 0,
                "N": 16,
                "b": 1,
                "c": "76.92308",
                "d": 0,
                "diff": None,
                "f": 3,
                "h": 10,
                "m": 1,
                "n": 13,
                "p": 2,
                "s": 3,
            },
        }
        report.add_session(
            Session(
                sessionid=3, session_type=SessionType.uploaded, flags=["integration"]
            )
        )
        pprint.pprint(self.convert_report_to_better_readable(report))
        expected_result = {
            "archive": {
                "file_1.go": [
                    (
                        1,
                        1,
                        None,
                        [[0, 1, None, None, None], [2, 1, None, None, None]],
                        None,
                        (10, 2),
                    ),
                    (
                        2,
                        1,
                        None,
                        [[0, 1, None, None, None], [2, 1, None, None, None]],
                        None,
                        (10, 2),
                    ),
                    (3, 1, None, [[0, 1, None, None, None]], None, (10, 2)),
                    (5, 1, None, [[2, 1, None, None, None]], None, (10, 2)),
                    (6, 1, None, [[0, 1, None, None, None]], None, (10, 2)),
                    (7, 1, None, [[2, 1, None, None, None]], None, (10, 2)),
                    (
                        8,
                        1,
                        None,
                        [[2, 1, None, None, None], [0, 1, None, None, None]],
                        None,
                        (10, 2),
                    ),
                ],
                "file_2.py": [
                    (
                        12,
                        1,
                        None,
                        [[0, 1, None, None, None], [2, 0, None, None, None]],
                        None,
                        None,
                    ),
                    (51, "1/3", "b", [[0, "1/3", None, None, None]], None, None),
                ],
            },
            "report": {
                "files": {
                    "file_1.go": [
                        0,
                        [0, 7, 7, 0, 0, "100", 0, 0, 0, 0, 70, 14, 0],
                        [[0, 8, 8, 0, 0, "100", 0, 0, 0, 0, 80, 16, 0]],
                        None,
                    ],
                    "file_2.py": [
                        1,
                        [0, 2, 1, 0, 1, "50.00000", 1, 0, 0, 0, 0, 0, 0],
                        [[0, 2, 1, 0, 1, "50.00000", 1, 0, 0, 0, 0, 0, 0]],
                        None,
                    ],
                },
                "sessions": {
                    "0": {
                        "N": None,
                        "a": None,
                        "c": None,
                        "d": None,
                        "e": None,
                        "f": ["unit"],
                        "j": None,
                        "n": None,
                        "p": None,
                        "st": "uploaded",
                        "se": {},
                        "t": None,
                        "u": None,
                    },
                    "2": {
                        "N": None,
                        "a": None,
                        "c": None,
                        "d": None,
                        "e": None,
                        "f": None,
                        "j": None,
                        "n": None,
                        "p": None,
                        "st": "uploaded",
                        "se": {},
                        "t": None,
                        "u": None,
                    },
                    "3": {
                        "N": None,
                        "a": None,
                        "c": None,
                        "d": None,
                        "e": None,
                        "f": ["integration"],
                        "j": None,
                        "n": None,
                        "p": None,
                        "st": "uploaded",
                        "se": {},
                        "t": None,
                        "u": None,
                    },
                },
            },
            "totals": {
                "C": 70,
                "M": 0,
                "N": 14,
                "b": 1,
                "c": "88.88889",
                "d": 0,
                "diff": None,
                "f": 2,
                "h": 8,
                "m": 0,
                "n": 9,
                "p": 1,
                "s": 3,
            },
        }
        res = self.convert_report_to_better_readable(report)
        assert res["archive"] == expected_result["archive"]
        assert res["report"] == expected_result["report"]
        assert res["totals"] == expected_result["totals"]
        assert res == expected_result
