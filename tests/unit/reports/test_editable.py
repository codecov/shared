import dataclasses
from fractions import Fraction
from json import loads
from pathlib import Path
from typing import List

import pytest

from shared.reports.editable import EditableReport, EditableReportFile
from shared.reports.resources import ReportFile, ReportFileSummary, Session
from shared.reports.types import (
    CoverageDatapoint,
    LineSession,
    ReportLine,
    ReportTotals,
)
from shared.utils.merge import merge_coverage
from shared.utils.sessions import SessionType

current_file = Path(__file__)


# This immitates what a report.labels_index looks like
# It's an map idx -> label, so we can go from CoverageDatapoint.label_id to the actual label
# typically via Report.lookup_label_by_id
def lookup_label(label_id: int) -> str:
    lookup_table = {
        1: "simple",
        2: "one_label",
        3: "another_label",
        4: "something",
        5: "label_1",
        6: "label_2",
        7: "label_3",
        8: "label_4",
        9: "label_5",
        10: "label_6",
    }
    return lookup_table[label_id]


def create_sample_line(
    *, coverage, sessionid=None, list_of_lists_of_label_ids: List[List[int]] = None
):
    datapoints = [
        CoverageDatapoint(
            sessionid=sessionid,
            coverage=coverage,
            coverage_type=None,
            label_ids=label_ids,
        )
        for label_ids in (list_of_lists_of_label_ids or [[]])
    ]
    return ReportLine.create(
        coverage=coverage,
        sessions=[
            (
                LineSession(
                    id=sessionid,
                    coverage=coverage,
                )
            )
        ],
        datapoints=datapoints,
    )


def test_merge_coverage():
    assert merge_coverage(0.5, Fraction(3, 4)) == Fraction(3, 4)
    assert merge_coverage(2, Fraction(3, 4)) == 2


class TestEditableReportHelpers(object):
    def test_line_without_session(self):
        line = ReportLine.create(1, None, [LineSession(1, 0), LineSession(0, 1)])
        assert EditableReportFile.line_without_session(line, 1) == ReportLine.create(
            1, None, [LineSession(0, 1)]
        )
        assert EditableReportFile.line_without_session(line, 0) == ReportLine.create(
            0, None, [LineSession(1, 0)]
        )
        assert (
            EditableReportFile.line_without_session(
                EditableReportFile.line_without_session(line, 0), 1
            )
            == ""
        )

    def test_line_without_labels(self):
        line = ReportLine.create(
            "2/2",
            None,
            [LineSession(1, 0), LineSession(0, 1)],
            datapoints=[
                CoverageDatapoint(1, 0, None, [5, 6]),
                CoverageDatapoint(1, 0, None, [7, 6]),
                CoverageDatapoint(0, 1, None, [5, 6]),
                CoverageDatapoint(0, "1/2", None, [5, 8]),
                CoverageDatapoint(0, "1/2", None, [9, 10]),
                CoverageDatapoint(0, 0, None, [10, 8]),
            ],
        )
        assert EditableReportFile.line_without_labels(
            line, [1], [5]
        ) == ReportLine.create(
            "2/2",
            None,
            [LineSession(1, 0), LineSession(0, 1)],
            datapoints=[
                CoverageDatapoint(1, 0, None, [7, 6]),
                CoverageDatapoint(0, 1, None, [5, 6]),
                CoverageDatapoint(0, "1/2", None, [5, 8]),
                CoverageDatapoint(0, "1/2", None, [9, 10]),
                CoverageDatapoint(0, 0, None, [10, 8]),
            ],
        )
        assert EditableReportFile.line_without_labels(
            line, [1, 0], [5]
        ) == ReportLine.create(
            "1/2",
            None,
            [LineSession(1, 0), LineSession(0, 1)],
            datapoints=[
                CoverageDatapoint(1, 0, None, [7, 6]),
                CoverageDatapoint(0, "1/2", None, [9, 10]),
                CoverageDatapoint(0, 0, None, [10, 8]),
            ],
        )
        assert EditableReportFile.line_without_labels(
            line, [1], [5, 6]
        ) == ReportLine.create(
            "2/2",
            None,
            [LineSession(0, 1)],
            datapoints=[
                CoverageDatapoint(0, 1, None, [5, 6]),
                CoverageDatapoint(0, "1/2", None, [5, 8]),
                CoverageDatapoint(0, "1/2", None, [9, 10]),
                CoverageDatapoint(0, 0, None, [10, 8]),
            ],
        )
        assert EditableReportFile.line_without_labels(
            line, [0, 1], [5, 6]
        ) == ReportLine.create(
            "1/2",
            None,
            [LineSession(0, 1)],
            datapoints=[
                CoverageDatapoint(0, "1/2", None, [9, 10]),
                CoverageDatapoint(0, 0, None, [10, 8]),
            ],
        )
        assert EditableReportFile.line_without_labels(line, [0, 1], [5, 6, 10]) == ""
        assert EditableReportFile.line_without_labels(
            line, [0, 1], [5, 6, 9]
        ) == ReportLine.create(
            0,
            None,
            [LineSession(0, 1)],
            datapoints=[
                CoverageDatapoint(0, 0, None, [10, 8]),
            ],
        )
        assert EditableReportFile.line_without_labels(line, [0, 1], [5, 6, 10]) == ""

    def test_delete_labels_session_without_datapoints(self):
        line = ReportLine.create(
            1,
            None,
            [LineSession(0, 1), LineSession(1, 1), LineSession(2, 0)],
            datapoints=[
                CoverageDatapoint(1, 1, None, [5, 6]),
                CoverageDatapoint(1, 0, None, [7, 6]),
                CoverageDatapoint(2, 0, None, [10]),
            ],
        )
        assert EditableReportFile.line_without_labels(
            line, [1], [5, 6, 10]
        ) == ReportLine.create(
            1,
            None,
            [LineSession(0, 1), LineSession(2, 0)],
            datapoints=[CoverageDatapoint(2, 0, None, [10])],
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
            (
                1,
                ReportLine.create(
                    coverage=1, sessions=[LineSession(0, 1), LineSession(1, 0)]
                ),
            ),
            (
                4,
                ReportLine.create(
                    coverage=0, sessions=[LineSession(0, 0), LineSession(1, 0)]
                ),
            ),
            (
                5,
                ReportLine.create(
                    coverage=1, sessions=[LineSession(0, 1), LineSession(1, 1)]
                ),
            ),
            (
                6,
                ReportLine.create(
                    coverage=1, sessions=[LineSession(0, 0), LineSession(1, 1)]
                ),
            ),
            (
                9,
                ReportLine.create(
                    coverage=1, sessions=[LineSession(0, 1), LineSession(1, "1/2")]
                ),
            ),
            (
                10,
                ReportLine.create(
                    coverage=1, sessions=[LineSession(0, "1/2"), LineSession(1, 1)]
                ),
            ),
            (13, ReportLine.create(coverage=1, sessions=[LineSession(0, 1)])),
            (14, ReportLine.create(coverage=1, sessions=[LineSession(1, 1)])),
            (
                15,
                ReportLine.create(
                    coverage="1/2", sessions=[LineSession(0, "1/2"), LineSession(1, 0)]
                ),
            ),
            (
                16,
                ReportLine.create(
                    coverage="1/2", sessions=[LineSession(0, 0), LineSession(1, "1/2")]
                ),
            ),
        ]
        assert list(report_file.lines) == expected_result

    def test_delete_labels_empty_line_deleted(self):
        first_file = EditableReportFile("first_file.py")
        first_file.append(
            1,
            create_sample_line(
                coverage=1,
                sessionid=2,
                list_of_lists_of_label_ids=[[1]],
            ),
        )
        assert list(first_file.lines) == [
            (
                1,
                ReportLine(
                    coverage=1,
                    type=None,
                    sessions=[
                        LineSession(
                            id=2,
                            coverage=1,
                            branches=None,
                            partials=None,
                            complexity=None,
                        )
                    ],
                    messages=None,
                    complexity=None,
                    datapoints=[
                        CoverageDatapoint(
                            sessionid=2,
                            coverage=1,
                            coverage_type=None,
                            label_ids=[1],
                        )
                    ],
                ),
            )
        ]
        first_file.delete_labels([2], [1])
        assert list(first_file.lines) == []

    def test_merge_not_previously_set_sessions_header(self):
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
        assert report_file.details == {}
        new_chunks = "\n".join(
            [
                "{}",
                "[1, null, [[0, 1], [2, 0]]]",
                "",
                "",
                "[0, null, [[2, 0], [1, 0]]]",
                "[1, null, [[2, 1], [3, 1]]]",
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
                '["1/2", null, [[2, 0], [1, "1/2"]]]',
            ]
        )
        new_report_file = ReportFile(name="file.py", lines=new_chunks)
        report_file.merge(new_report_file)
        assert report_file.details == {"present_sessions": [0, 1, 2, 3]}

    def test_details(self):
        chunks = "\n".join(['{"some_field": "nah"}', "[1, null, [[0, 1], [1, 0]]]", ""])
        report_file = EditableReportFile(name="file.py", lines=chunks)
        assert report_file.details == {"some_field": "nah"}

    def test_encode_with_details_with_present_sessions_as_set(self):
        chunks = "\n".join(["", "[1, null, [[0, 1], [1, 0]]]", ""])
        report_file = EditableReportFile(name="file.py", lines=chunks)
        report_file._details = {"present_sessions": set([1, 2, 4])}
        expected_result = "\n".join(
            ['{"present_sessions":[1,2,4]}', "[1, null, [[0, 1], [1, 0]]]"]
        )
        assert report_file._encode() == expected_result

    def test_encode_with_details_with_present_sessions_as_empty_set(self):
        chunks = "\n".join(["", "[1, null, [[0, 1], [1, 0]]]", ""])
        report_file = EditableReportFile(name="file.py", lines=chunks)
        report_file._details = {"present_sessions": set()}
        expected_result = "\n".join(
            ['{"present_sessions":[]}', "[1, null, [[0, 1], [1, 0]]]"]
        )
        assert report_file._encode() == expected_result

    def test_encode_with_details_with_present_sessions_as_list(self):
        chunks = "\n".join(["", "[1, null, [[0, 1], [1, 0]]]", ""])
        report_file = EditableReportFile(name="file.py", lines=chunks)
        report_file._details = {"present_sessions": [10, 2, 4]}
        expected_result = "\n".join(
            ['{"present_sessions":[2,4,10]}', "[1, null, [[0, 1], [1, 0]]]"]
        )
        assert report_file._encode() == expected_result

    def test_encode_with_details_with_nothing(self):
        chunks = "\n".join(["", "[1, null, [[0, 1], [1, 0]]]", ""])
        report_file = EditableReportFile(name="file.py", lines=chunks)
        report_file._details = {}
        expected_result = "\n".join(["{}", "[1, null, [[0, 1], [1, 0]]]"])
        assert report_file._encode() == expected_result

    def test_encode_with_details_with_none(self):
        chunks = "\n".join(["", "[1, null, [[0, 1], [1, 0]]]", ""])
        report_file = EditableReportFile(name="file.py", lines=chunks)
        report_file._details = None
        expected_result = "\n".join(["null", "[1, null, [[0, 1], [1, 0]]]"])
        assert report_file._encode() == expected_result

    def test_merge_already_previously_set_sessions_header(self):
        chunks = "\n".join(
            [
                '{"present_sessions":[0,1]}',
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
        assert report_file.details == {"present_sessions": [0, 1]}
        new_chunks = "\n".join(
            [
                "{}",
                "[1, null, [[0, 1], [2, 0]]]",
                "",
                "",
                "[0, null, [[2, 0], [1, 0]]]",
                "[1, null, [[2, 1], [3, 1]]]",
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
                '["1/2", null, [[2, 0], [1, "1/2"]]]',
            ]
        )
        new_report_file = ReportFile(name="file.py", lines=new_chunks)
        report_file.merge(new_report_file)
        assert report_file.details == {"present_sessions": [0, 1, 2, 3]}

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
            (
                1,
                ReportLine.create(
                    coverage=1, sessions=[LineSession(0, 1), LineSession(1, 0)]
                ),
            ),
            (
                4,
                ReportLine.create(
                    coverage=0, sessions=[LineSession(0, 0), LineSession(1, 0)]
                ),
            ),
            (
                5,
                ReportLine.create(
                    coverage=1, sessions=[LineSession(0, 1), LineSession(1, 1)]
                ),
            ),
            (
                6,
                ReportLine.create(
                    coverage=1, sessions=[LineSession(0, 0), LineSession(1, 1)]
                ),
            ),
            (
                9,
                ReportLine.create(
                    coverage=1, sessions=[LineSession(0, 1), LineSession(1, "1/2")]
                ),
            ),
            (
                10,
                ReportLine.create(
                    coverage=1, sessions=[LineSession(0, "1/2"), LineSession(1, 1)]
                ),
            ),
            (13, ReportLine.create(coverage=1, sessions=[LineSession(0, 1)])),
            (14, ReportLine.create(coverage=1, sessions=[LineSession(1, 1)])),
            (
                15,
                ReportLine.create(
                    coverage="1/2", sessions=[LineSession(0, "1/2"), LineSession(1, 0)]
                ),
            ),
            (
                16,
                ReportLine.create(
                    coverage="1/2", sessions=[LineSession(0, 0), LineSession(1, "1/2")]
                ),
            ),
        ]
        assert list(report_file.lines) == original_lines
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
        assert report_file.details == {"present_sessions": [0]}

    def test_delete_session_not_present(self):
        chunks = "\n".join(
            [
                '{"present_sessions":[0,1]}',
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
            (
                1,
                ReportLine.create(
                    coverage=1, sessions=[LineSession(0, 1), LineSession(1, 0)]
                ),
            ),
            (
                4,
                ReportLine.create(
                    coverage=0, sessions=[LineSession(0, 0), LineSession(1, 0)]
                ),
            ),
            (
                5,
                ReportLine.create(
                    coverage=1, sessions=[LineSession(0, 1), LineSession(1, 1)]
                ),
            ),
            (
                6,
                ReportLine.create(
                    coverage=1, sessions=[LineSession(0, 0), LineSession(1, 1)]
                ),
            ),
            (
                9,
                ReportLine.create(
                    coverage=1, sessions=[LineSession(0, 1), LineSession(1, "1/2")]
                ),
            ),
            (
                10,
                ReportLine.create(
                    coverage=1, sessions=[LineSession(0, "1/2"), LineSession(1, 1)]
                ),
            ),
            (13, ReportLine.create(coverage=1, sessions=[LineSession(0, 1)])),
            (14, ReportLine.create(coverage=1, sessions=[LineSession(1, 1)])),
            (
                15,
                ReportLine.create(
                    coverage="1/2", sessions=[LineSession(0, "1/2"), LineSession(1, 0)]
                ),
            ),
            (
                16,
                ReportLine.create(
                    coverage="1/2", sessions=[LineSession(0, 0), LineSession(1, "1/2")]
                ),
            ),
        ]
        assert list(report_file.lines) == original_lines
        report_file.delete_session(3)
        assert list(report_file.lines) == original_lines
        assert report_file.details == {"present_sessions": [0, 1]}

    def test_delete_multiple_sessions(self):
        chunks = "\n".join(
            [
                '{"present_sessions":[0,1,2,3]}',
                "[1, null, [[0, 1], [1, 0]]]",
                "",
                "",
                "[0, null, [[2, 0], [1, 0]]]",
                "[1, null, [[0, 1], [3, 1]]]",
                "[1, null, [[0, 0], [1, 1]]]",
                "",
                "",
                '[1, null, [[0, 1], [1, "1/2"], [2, 1], [3, 1]]]',
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
            (
                1,
                ReportLine.create(
                    coverage=1, sessions=[LineSession(0, 1), LineSession(1, 0)]
                ),
            ),
            (
                4,
                ReportLine.create(
                    coverage=0, sessions=[LineSession(2, 0), LineSession(1, 0)]
                ),
            ),
            (
                5,
                ReportLine.create(
                    coverage=1, sessions=[LineSession(0, 1), LineSession(3, 1)]
                ),
            ),
            (
                6,
                ReportLine.create(
                    coverage=1, sessions=[LineSession(0, 0), LineSession(1, 1)]
                ),
            ),
            (
                9,
                ReportLine.create(
                    coverage=1,
                    sessions=[
                        LineSession(0, 1),
                        LineSession(1, "1/2"),
                        LineSession(2, 1),
                        LineSession(3, 1),
                    ],
                ),
            ),
            (
                10,
                ReportLine.create(
                    coverage=1, sessions=[LineSession(0, "1/2"), LineSession(1, 1)]
                ),
            ),
            (13, ReportLine.create(coverage=1, sessions=[LineSession(0, 1)])),
            (14, ReportLine.create(coverage=1, sessions=[LineSession(1, 1)])),
            (
                15,
                ReportLine.create(
                    coverage="1/2", sessions=[LineSession(0, "1/2"), LineSession(1, 0)]
                ),
            ),
            (
                16,
                ReportLine.create(
                    coverage="1/2", sessions=[LineSession(0, 0), LineSession(1, "1/2")]
                ),
            ),
        ]
        assert list(report_file.lines) == original_lines
        report_file.delete_multiple_sessions([1, 3, 5])
        expected_result = [
            (1, ReportLine.create(coverage=1, sessions=[LineSession(0, 1)])),
            (4, ReportLine.create(coverage=0, sessions=[LineSession(2, 0)])),
            (5, ReportLine.create(coverage=1, sessions=[LineSession(0, 1)])),
            (6, ReportLine.create(coverage=0, sessions=[LineSession(0, 0)])),
            (
                9,
                ReportLine.create(
                    coverage=1, sessions=[LineSession(0, 1), LineSession(2, 1)]
                ),
            ),
            (10, ReportLine.create(coverage="1/2", sessions=[LineSession(0, "1/2")])),
            (13, ReportLine.create(coverage=1, sessions=[LineSession(0, 1)])),
            (15, ReportLine.create(coverage="1/2", sessions=[LineSession(0, "1/2")])),
            (16, ReportLine.create(coverage=0, sessions=[LineSession(0, 0)])),
        ]
        res = list(report_file.lines)
        assert res[0] == expected_result[0]
        assert res == expected_result
        assert report_file.details == {"present_sessions": [0, 2]}


@pytest.fixture
def sample_report():
    report = EditableReport()
    first_file = EditableReportFile("file_1.go")
    first_file.append(
        1,
        ReportLine.create(
            coverage=1,
            sessions=[LineSession(0, 1), LineSession(1, 1), LineSession(2, 1)],
            complexity=(10, 2),
        ),
    )
    first_file.append(
        2,
        ReportLine.create(
            coverage=1,
            sessions=[LineSession(0, 1), LineSession(1, "1/2"), LineSession(2, 1)],
            complexity=(10, 2),
        ),
    )
    first_file.append(
        3,
        ReportLine.create(coverage=1, sessions=[LineSession(0, 1)], complexity=(10, 2)),
    )
    first_file.append(
        4,
        ReportLine.create(coverage=1, sessions=[LineSession(1, 1)], complexity=(10, 2)),
    )
    first_file.append(
        5,
        ReportLine.create(coverage=1, sessions=[LineSession(2, 1)], complexity=(10, 2)),
    )
    first_file.append(
        6,
        ReportLine.create(
            coverage=1,
            sessions=[LineSession(0, 1), LineSession(1, 1)],
            complexity=(10, 2),
        ),
    )
    first_file.append(
        7,
        ReportLine.create(
            coverage=1,
            sessions=[LineSession(1, 1), LineSession(2, 1)],
            complexity=(10, 2),
        ),
    )
    first_file.append(
        8,
        ReportLine.create(
            coverage=1,
            sessions=[LineSession(2, 1), LineSession(0, 1)],
            complexity=(10, 2),
        ),
    )
    second_file = EditableReportFile("file_2.py")
    second_file.append(
        12,
        ReportLine.create(
            coverage=1,
            sessions=[LineSession(0, 1), LineSession(1, "1/2"), LineSession(2, 0)],
        ),
    )
    second_file.append(
        51,
        ReportLine.create(
            coverage="1/2",
            type="b",
            sessions=[LineSession(0, "1/3"), LineSession(1, "1/2")],
        ),
    )
    single_session_file = EditableReportFile("single_session_file.c")
    single_session_file.append(
        101, ReportLine.create(coverage="1/2", sessions=[LineSession(1, "1/2")])
    )
    single_session_file.append(
        110, ReportLine.create(coverage=1, sessions=[LineSession(1, 1)])
    )
    single_session_file.append(
        111, ReportLine.create(coverage=0, sessions=[LineSession(1, 0)])
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
    @pytest.fixture
    def sample_with_labels_report(self):
        first_report = EditableReport()
        first_report.add_session(
            Session(
                flags=["enterprise"],
                sessionid=0,
                session_type=SessionType.carriedforward,
            )
        )
        first_report.add_session(
            Session(
                flags=["enterprise"], sessionid=1, session_type=SessionType.uploaded
            )
        )
        first_report.add_session(
            Session(
                flags=["unit"], sessionid=2, session_type=SessionType.carriedforward
            )
        )
        first_report.add_session(
            Session(flags=["unrelated"], sessionid=3, session_type=SessionType.uploaded)
        )
        first_file = EditableReportFile("first_file.py")
        c = 0
        for list_of_lists_of_label_ids in [
            [[2]],
            [[3]],
            [[3], [2]],
            [[3, 2]],
            [[4]],
        ]:
            for sessionid in range(4):
                first_file.append(
                    c % 7 + 1,
                    create_sample_line(
                        coverage=c,
                        sessionid=sessionid,
                        list_of_lists_of_label_ids=list_of_lists_of_label_ids,
                    ),
                )
                c += 1
        first_file.append(23, ReportLine.create(1, sessions=[LineSession(1, 1)]))
        second_file = EditableReportFile("second_file.py")
        first_report.append(first_file)
        first_report.append(second_file)
        # print(self.convert_report_to_better_readable(first_report)["archive"])
        assert self.convert_report_to_better_readable(first_report)["archive"] == {
            "first_file.py": [
                (
                    1,
                    14,
                    None,
                    [
                        [0, 0, None, None, None],
                        [3, 7, None, None, None],
                        [2, 14, None, None, None],
                    ],
                    None,
                    None,
                    [
                        (0, 0, None, [2]),
                        (2, 14, None, [3, 2]),
                        (3, 7, None, [3]),
                    ],
                ),
                (
                    2,
                    15,
                    None,
                    [
                        [1, 1, None, None, None],
                        [0, 8, None, None, None],
                        [3, 15, None, None, None],
                    ],
                    None,
                    None,
                    [
                        (0, 8, None, [2]),
                        (0, 8, None, [3]),
                        (1, 1, None, [2]),
                        (3, 15, None, [3, 2]),
                    ],
                ),
                (
                    3,
                    16,
                    None,
                    [
                        [2, 2, None, None, None],
                        [1, 9, None, None, None],
                        [0, 16, None, None, None],
                    ],
                    None,
                    None,
                    [
                        (0, 16, None, [4]),
                        (1, 9, None, [2]),
                        (1, 9, None, [3]),
                        (2, 2, None, [2]),
                    ],
                ),
                (
                    4,
                    17,
                    None,
                    [
                        [3, 3, None, None, None],
                        [2, 10, None, None, None],
                        [1, 17, None, None, None],
                    ],
                    None,
                    None,
                    [
                        (1, 17, None, [4]),
                        (2, 10, None, [2]),
                        (2, 10, None, [3]),
                        (3, 3, None, [2]),
                    ],
                ),
                (
                    5,
                    18,
                    None,
                    [
                        [0, 4, None, None, None],
                        [3, 11, None, None, None],
                        [2, 18, None, None, None],
                    ],
                    None,
                    None,
                    [
                        (0, 4, None, [3]),
                        (2, 18, None, [4]),
                        (3, 11, None, [2]),
                        (3, 11, None, [3]),
                    ],
                ),
                (
                    6,
                    19,
                    None,
                    [
                        [1, 5, None, None, None],
                        [0, 12, None, None, None],
                        [3, 19, None, None, None],
                    ],
                    None,
                    None,
                    [
                        (0, 12, None, [3, 2]),
                        (1, 5, None, [3]),
                        (3, 19, None, [4]),
                    ],
                ),
                (
                    7,
                    13,
                    None,
                    [[2, 6, None, None, None], [1, 13, None, None, None]],
                    None,
                    None,
                    [
                        (1, 13, None, [3, 2]),
                        (2, 6, None, [3]),
                    ],
                ),
                (23, 1, None, [[1, 1, None, None, None]], None, None),
            ]
        }

        return first_report

    def test_delete_labels_empty_file_deleted(self):
        report = EditableReport()
        first_file = EditableReportFile("first_file.py")
        some_other_file = EditableReportFile("someother.py")
        some_other_file.append(1, ReportLine.create(1, sessions=[LineSession(2, 1)]))
        first_file.append(
            1,
            create_sample_line(
                coverage=1,
                sessionid=2,
                list_of_lists_of_label_ids=[[1]],
            ),
        )
        report.append(first_file)
        report.append(some_other_file)
        assert report.files == ["first_file.py", "someother.py"]
        assert self.convert_report_to_better_readable(report)["archive"] == {
            "first_file.py": [
                (
                    1,
                    1,
                    None,
                    [[2, 1, None, None, None]],
                    None,
                    None,
                    [(2, 1, None, [1])],
                )
            ],
            "someother.py": [(1, 1, None, [[2, 1, None, None, None]], None, None)],
        }
        report.delete_labels([2], [1])
        assert self.convert_report_to_better_readable(report)["archive"] == {
            "someother.py": [(1, 1, None, [[2, 1, None, None, None]], None, None)]
        }

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
                    datapoints,
                ) = dataclasses.astuple(line)
                sessions = [list(s) for s in sessions]
                lines.append(
                    (line_number, coverage, line_type, sessions, messages, complexity)
                    if datapoints is None
                    else (
                        line_number,
                        coverage,
                        line_type,
                        sessions,
                        messages,
                        complexity,
                        datapoints,
                    )
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
        assert all(
            (isinstance(x, EditableReportFile) or x is None) for x in report._chunks
        )

    def test_init_deleted_chunks(self):
        with open(current_file.parent / "samples" / "chunks_02.txt", "r") as f:
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
        }
        assert all(
            (isinstance(x, EditableReportFile) or x is None) for x in report._chunks
        )
        assert report._chunks[1] is None
        assert list(report._chunks[0].lines) == [
            (
                1,
                ReportLine.create(
                    coverage=1,
                    type=None,
                    sessions=[
                        LineSession(
                            id=0,
                            coverage=1,
                            branches=None,
                            partials=None,
                            complexity=None,
                        )
                    ],
                    messages=None,
                    complexity=None,
                ),
            ),
            (
                3,
                ReportLine.create(
                    coverage=1,
                    type=None,
                    sessions=[
                        LineSession(
                            id=1,
                            coverage=1,
                            branches=None,
                            partials=None,
                            complexity=None,
                        )
                    ],
                    messages=None,
                    complexity=None,
                ),
            ),
            (
                5,
                ReportLine.create(
                    coverage=1,
                    type=None,
                    sessions=[
                        LineSession(
                            id=0,
                            coverage=1,
                            branches=None,
                            partials=None,
                            complexity=None,
                        )
                    ],
                    messages=None,
                    complexity=None,
                ),
            ),
            (
                6,
                ReportLine.create(
                    coverage=1,
                    type=None,
                    sessions=[
                        LineSession(
                            id=1,
                            coverage=1,
                            branches=None,
                            partials=None,
                            complexity=None,
                        )
                    ],
                    messages=None,
                    complexity=None,
                ),
            ),
            (
                8,
                ReportLine.create(
                    coverage=1,
                    type=None,
                    sessions=[
                        LineSession(
                            id=0,
                            coverage=1,
                            branches=None,
                            partials=None,
                            complexity=None,
                        )
                    ],
                    messages=None,
                    complexity=None,
                ),
            ),
            (
                10,
                ReportLine.create(
                    coverage=1,
                    type=None,
                    sessions=[
                        LineSession(
                            id=1,
                            coverage=1,
                            branches=None,
                            partials=None,
                            complexity=None,
                        )
                    ],
                    messages=None,
                    complexity=None,
                ),
            ),
            (
                12,
                ReportLine.create(
                    coverage=1,
                    type=None,
                    sessions=[
                        LineSession(
                            id=0,
                            coverage=1,
                            branches=None,
                            partials=None,
                            complexity=None,
                        )
                    ],
                    messages=None,
                    complexity=None,
                ),
            ),
        ]
        assert list(report._chunks[2].lines) == [
            (
                1,
                ReportLine.create(
                    coverage=1,
                    type=None,
                    sessions=[
                        LineSession(
                            id=0,
                            coverage=1,
                            branches=None,
                            partials=None,
                            complexity=None,
                        )
                    ],
                    messages=None,
                    complexity=None,
                ),
            ),
            (
                2,
                ReportLine.create(
                    coverage=1,
                    type=None,
                    sessions=[
                        LineSession(
                            id=0,
                            coverage=1,
                            branches=None,
                            partials=None,
                            complexity=None,
                        )
                    ],
                    messages=None,
                    complexity=None,
                ),
            ),
            (
                5,
                ReportLine.create(
                    coverage=0,
                    type=None,
                    sessions=[
                        LineSession(
                            id=0,
                            coverage=0,
                            branches=None,
                            partials=None,
                            complexity=None,
                        )
                    ],
                    messages=None,
                    complexity=None,
                ),
            ),
        ]

    def test_delete_session(self, sample_report):
        report = sample_report

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
                        {
                            "meta": {"session_count": 1},
                            "0": [0, 8, 8, 0, 0, "100", 0, 0, 0, 0, 80, 16],
                        },
                        None,
                    ],
                    "file_2.py": [
                        1,
                        [0, 2, 1, 0, 1, "50.00000", 1, 0, 0, 0, 0, 0, 0],
                        {
                            "meta": {"session_count": 1},
                            "0": [0, 2, 1, 0, 1, "50.00000", 1],
                        },
                        None,
                    ],
                    "single_session_file.c": [
                        2,
                        [0, 3, 1, 1, 1, "33.33333", 0, 0, 0, 0, 0, 0, 0],
                        {
                            "meta": {"session_count": 1},
                            "0": [0, 3, 1, 1, 1, "33.33333"],
                        },
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
                        {
                            "meta": {"session_count": 1},
                            "0": [0, 8, 8, 0, 0, "100", 0, 0, 0, 0, 80, 16],
                        },
                        None,
                    ],
                    "file_2.py": [
                        1,
                        [0, 2, 1, 0, 1, "50.00000", 1, 0, 0, 0, 0, 0, 0],
                        {
                            "meta": {"session_count": 1},
                            "0": [0, 2, 1, 0, 1, "50.00000", 1],
                        },
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
                "c": None,
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
        old_readable = self.convert_report_to_better_readable(report)
        assert old_readable == {
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
                        {
                            "meta": {"session_count": 1},
                            "0": [0, 8, 8, 0, 0, "100", 0, 0, 0, 0, 80, 16],
                        },
                        None,
                    ],
                    "file_2.py": [
                        1,
                        [0, 2, 1, 0, 1, "50.00000", 1, 0, 0, 0, 0, 0, 0],
                        {
                            "meta": {"session_count": 1},
                            "0": [0, 2, 1, 0, 1, "50.00000", 1],
                        },
                        None,
                    ],
                    "single_session_file.c": [
                        2,
                        [0, 3, 1, 1, 1, "33.33333", 0, 0, 0, 0, 0, 0, 0],
                        {
                            "meta": {"session_count": 1},
                            "0": [0, 3, 1, 1, 1, "33.33333"],
                        },
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
        res = self.convert_report_to_better_readable(report)
        assert res["archive"] == old_readable["archive"]
        assert res["report"]["files"] == old_readable["report"]["files"]
        assert old_readable["totals"].pop("s") == 3
        assert res["totals"].pop("s") == 4
        assert res["totals"] == old_readable["totals"]

    def test_delete_labels(self, sample_with_labels_report):
        sample_with_labels_report.delete_labels([0], [3])
        for file in sample_with_labels_report:
            for ln, line in file.lines:
                # some lines previously didnt have datapoints
                if line.datapoints:
                    for dp in line.datapoints:
                        assert dp.sessionid != 0 or 3 not in dp.label_ids
        print(sample_with_labels_report)
        print(sample_with_labels_report._files)
        res = self.convert_report_to_better_readable(sample_with_labels_report)
        expected_result = {
            "totals": {
                "f": 1,
                "n": 8,
                "h": 8,
                "m": 0,
                "p": 0,
                "c": "100",
                "b": 0,
                "d": 0,
                "M": 0,
                "s": 4,
                "C": 0,
                "N": 0,
                "diff": None,
            },
            "report": {
                "files": {
                    "first_file.py": [
                        0,
                        [0, 8, 8, 0, 0, "100", 0, 0, 0, 0, 0, 0, 0],
                        {
                            "meta": {"session_count": 4},
                            "3": [0, 8, 8, 0, 0, "100"],
                        },
                        None,
                    ]
                },
                "sessions": {
                    "0": {
                        "t": None,
                        "d": None,
                        "a": None,
                        "f": ["enterprise"],
                        "c": None,
                        "n": None,
                        "N": None,
                        "j": None,
                        "u": None,
                        "p": None,
                        "e": None,
                        "st": "carriedforward",
                        "se": {},
                    },
                    "1": {
                        "t": None,
                        "d": None,
                        "a": None,
                        "f": ["enterprise"],
                        "c": None,
                        "n": None,
                        "N": None,
                        "j": None,
                        "u": None,
                        "p": None,
                        "e": None,
                        "st": "uploaded",
                        "se": {},
                    },
                    "2": {
                        "t": None,
                        "d": None,
                        "a": None,
                        "f": ["unit"],
                        "c": None,
                        "n": None,
                        "N": None,
                        "j": None,
                        "u": None,
                        "p": None,
                        "e": None,
                        "st": "carriedforward",
                        "se": {},
                    },
                    "3": {
                        "t": None,
                        "d": None,
                        "a": None,
                        "f": ["unrelated"],
                        "c": None,
                        "n": None,
                        "N": None,
                        "j": None,
                        "u": None,
                        "p": None,
                        "e": None,
                        "st": "uploaded",
                        "se": {},
                    },
                },
            },
            "archive": {
                "first_file.py": [
                    (
                        1,
                        14,
                        None,
                        [
                            [0, 0, None, None, None],
                            [3, 7, None, None, None],
                            [2, 14, None, None, None],
                        ],
                        None,
                        None,
                        [
                            (0, 0, None, [2]),
                            (2, 14, None, [3, 2]),
                            (3, 7, None, [3]),
                        ],
                    ),
                    (
                        2,
                        15,
                        None,
                        [
                            [1, 1, None, None, None],
                            [0, 8, None, None, None],
                            [3, 15, None, None, None],
                        ],
                        None,
                        None,
                        [
                            (0, 8, None, [2]),
                            (1, 1, None, [2]),
                            (3, 15, None, [3, 2]),
                        ],
                    ),
                    (
                        3,
                        16,
                        None,
                        [
                            [2, 2, None, None, None],
                            [1, 9, None, None, None],
                            [0, 16, None, None, None],
                        ],
                        None,
                        None,
                        [
                            (0, 16, None, [4]),
                            (1, 9, None, [2]),
                            (1, 9, None, [3]),
                            (2, 2, None, [2]),
                        ],
                    ),
                    (
                        4,
                        17,
                        None,
                        [
                            [3, 3, None, None, None],
                            [2, 10, None, None, None],
                            [1, 17, None, None, None],
                        ],
                        None,
                        None,
                        [
                            (1, 17, None, [4]),
                            (2, 10, None, [2]),
                            (2, 10, None, [3]),
                            (3, 3, None, [2]),
                        ],
                    ),
                    (
                        5,
                        18,
                        None,
                        [[3, 11, None, None, None], [2, 18, None, None, None]],
                        None,
                        None,
                        [
                            (2, 18, None, [4]),
                            (3, 11, None, [2]),
                            (3, 11, None, [3]),
                        ],
                    ),
                    (
                        6,
                        19,
                        None,
                        [[1, 5, None, None, None], [3, 19, None, None, None]],
                        None,
                        None,
                        [(1, 5, None, [3]), (3, 19, None, [4])],
                    ),
                    (
                        7,
                        13,
                        None,
                        [[2, 6, None, None, None], [1, 13, None, None, None]],
                        None,
                        None,
                        [
                            (1, 13, None, [3, 2]),
                            (2, 6, None, [3]),
                        ],
                    ),
                    (23, 1, None, [[1, 1, None, None, None]], None, None),
                ]
            },
        }
        assert res["report"]["sessions"] == expected_result["report"]["sessions"]
        assert (
            res["report"]["files"]["first_file.py"]
            == expected_result["report"]["files"]["first_file.py"]
        )
        assert res["report"]["files"] == expected_result["report"]["files"]
        assert res == expected_result
