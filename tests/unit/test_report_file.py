import pytest

from shared.reports.resources import ReportFile
from shared.reports.types import ReportLine


def format_lines_idx_and_coverage_only(lines):
    return [
        tuple(
            [
                idx,
                f"ReportLine(coverage={report_line.coverage})"
                if hasattr(report_line, "coverage")
                else report_line,
            ]
        )
        for idx, report_line in enumerate(lines, start=1)
    ]


@pytest.mark.unit
def test_shift_lines_by_diff_mixed_changes():
    file = ReportFile("file_1.go")
    # Coverage is the line number before the shift
    file.append(1, ReportLine.create(coverage=1))
    file.append(2, ReportLine.create(coverage=2))
    file.append(3, ReportLine.create(coverage=3))
    file.append(5, ReportLine.create(coverage=5))
    file.append(6, ReportLine.create(coverage=6))
    file.append(8, ReportLine.create(coverage=8))
    file.append(9, ReportLine.create(coverage=9))
    file.append(10, ReportLine.create(coverage=10))

    fake_diff = {
        "type": "modified",
        "before": None,
        "segments": [
            {
                "header": [3, 3, 3, 4],
                "lines": [
                    " some go code in line 3",
                    "-this line was removed",
                    "+this line was added",
                    "+this line was also added",
                    " ",
                ],
            },
            {
                "header": [9, 1, 10, 5],
                "lines": [
                    " some go code in line 9",
                    "+add",
                    "+add",
                    "+add",
                    "+add",
                ],
            },
        ],
    }
    file.shift_lines_by_diff(fake_diff)
    assert format_lines_idx_and_coverage_only(file._lines) == [
        (1, "ReportLine(coverage=1)"),
        (2, "ReportLine(coverage=2)"),
        (3, "ReportLine(coverage=3)"),
        (4, ""),
        (5, ""),
        (6, "ReportLine(coverage=5)"),
        (7, "ReportLine(coverage=6)"),
        (8, ""),
        (9, "ReportLine(coverage=8)"),
        (10, "ReportLine(coverage=9)"),
        (11, ""),
        (12, ""),
        (13, ""),
        (14, ""),
        (15, "ReportLine(coverage=10)"),
    ]


@pytest.mark.unit
def test_shift_lines_by_diff_only_adds():
    file = ReportFile("file_1.go")
    for i in range(1, 11):
        file.append(i, ReportLine.create(coverage=(i)))
    fake_diff = {
        "type": "modified",
        "before": None,
        "segments": [
            {
                "header": [3, 3, 3, 4],
                "lines": [
                    " some go code in line 3",
                    "+this line was added",
                    " ",
                    " ",
                ],
            },
            {
                "header": [8, 3, 9, 6],
                "lines": [
                    " some go code in line 8",
                    "+add",
                    " ",
                    "+add",
                    "+add",
                    " ",
                ],
            },
        ],
    }
    file.shift_lines_by_diff(fake_diff)
    assert format_lines_idx_and_coverage_only(file._lines) == [
        (1, "ReportLine(coverage=1)"),
        (2, "ReportLine(coverage=2)"),
        (3, "ReportLine(coverage=3)"),
        (4, ""),
        (5, "ReportLine(coverage=4)"),
        (6, "ReportLine(coverage=5)"),
        (7, "ReportLine(coverage=6)"),
        (8, "ReportLine(coverage=7)"),
        (9, "ReportLine(coverage=8)"),
        (10, ""),
        (11, "ReportLine(coverage=9)"),
        (12, ""),
        (13, ""),
        (14, "ReportLine(coverage=10)"),
    ]


@pytest.mark.unit
def test_shift_lines_by_diff_only_removals():
    file = ReportFile("file_1.go")
    for i in range(1, 11):
        file.append(i, ReportLine.create(coverage=(i)))
    fake_diff = {
        "type": "modified",
        "before": None,
        "segments": [
            {
                "header": [1, 3, 1, 2],
                "lines": [
                    " some go code in line 1",
                    "-this line was removed",
                    " ",
                ],
            },
            {
                "header": [5, 6, 4, 3],
                "lines": [
                    " some go code in line 5",
                    "-removed",
                    " ",
                    "-removed",
                    "-removed",
                    " ",
                ],
            },
        ],
    }
    file.shift_lines_by_diff(fake_diff)
    assert format_lines_idx_and_coverage_only(file._lines) == [
        (1, "ReportLine(coverage=1)"),
        (2, "ReportLine(coverage=3)"),
        (3, "ReportLine(coverage=4)"),
        (4, "ReportLine(coverage=5)"),
        (5, "ReportLine(coverage=7)"),
        (6, "ReportLine(coverage=10)"),
    ]


@pytest.mark.unit
def test_shift_lines_by_diff_wiki_example():
    file = ReportFile("file")
    for i in range(1, 31):
        file.append(i, ReportLine.create(coverage=(i)))
    fake_diff = {
        "segments": [
            {
                "header": [1, 3, 1, 9],
                "lines": [
                    "+This is an important",
                    "+notice! It should",
                    "+therefore be located at",
                    "+the beginning of this",
                    "+document!",
                    "+",
                    " This part of the",
                    " document has stayed the",
                    " same from version to",
                ],
            },
            {
                "header": [8, 13, 14, 8],
                "lines": [
                    " compress the size of the",
                    " changes.",
                    " ",
                    "-This paragraph contains",
                    "-text that is outdated.",
                    "-It will be deleted in the",
                    "-near future.",
                    "-",
                    " It is important to spell",
                    "-check this dokument. On",
                    "+check this document. On",
                    " the other hand, a",
                    " misspelled word isn't",
                    " the end of the world.",
                ],
            },
            {
                "header": [22, 3, 23, 7],
                "lines": [
                    " this paragraph needs to",
                    " be changed. Things can",
                    " be added after it.",
                    "+",
                    "+This paragraph contains",
                    "+important new additions",
                    "+to this document.",
                ],
            },
        ]
    }
    file.shift_lines_by_diff(fake_diff)
    assert format_lines_idx_and_coverage_only(file._lines) == [
        (1, ""),
        (2, ""),
        (3, ""),
        (4, ""),
        (5, ""),
        (6, ""),
        (7, "ReportLine(coverage=1)"),
        (8, "ReportLine(coverage=2)"),
        (9, "ReportLine(coverage=3)"),
        (10, "ReportLine(coverage=4)"),
        (11, "ReportLine(coverage=5)"),
        (12, "ReportLine(coverage=6)"),
        (13, "ReportLine(coverage=7)"),
        (14, "ReportLine(coverage=8)"),
        (15, "ReportLine(coverage=9)"),
        (16, "ReportLine(coverage=10)"),
        (17, "ReportLine(coverage=16)"),
        (18, ""),
        (19, "ReportLine(coverage=18)"),
        (20, "ReportLine(coverage=19)"),
        (21, "ReportLine(coverage=20)"),
        (22, "ReportLine(coverage=21)"),
        (23, "ReportLine(coverage=22)"),
        (24, "ReportLine(coverage=23)"),
        (25, "ReportLine(coverage=24)"),
        (26, ""),
        (27, ""),
        (28, ""),
        (29, ""),
        (30, "ReportLine(coverage=25)"),
        (31, "ReportLine(coverage=26)"),
        (32, "ReportLine(coverage=27)"),
        (33, "ReportLine(coverage=28)"),
        (34, "ReportLine(coverage=29)"),
        (35, "ReportLine(coverage=30)"),
    ]


@pytest.mark.unit
def test_shift_lines_by_diff_changes_to_no_code_at_eof():
    file = ReportFile("file")
    for i in range(1, 10):
        file.append(i, ReportLine.create(coverage=(i)))
    fake_diff = {
        "segments": [
            {
                "header": [1, 25, 1, 20],
                "lines": [
                    " This is an important",
                    " notice! It should",
                    " therefore be located at",
                    " the beginning of this",
                    " document!",
                    " ",
                    " This part of the",
                    " document has stayed the",
                    " same from version to",
                    " LAST LINE OF CODE IN THE FILE",
                    " ",
                    " #comment #comment",
                    " #comment #comment",
                    " #comment #comment",
                    " #comment #comment",
                    " #comment #comment",
                    " #comment #comment",
                    " #comment #comment",
                    " #comment #comment",
                    " #comment #comment",
                    "-#comment #comment",
                    "-#comment #comment",
                    "-#comment #comment",
                    "-#comment #comment",
                    "-#comment #comment",
                ],
            },
        ]
    }
    file.shift_lines_by_diff(fake_diff)
    assert format_lines_idx_and_coverage_only(file._lines) == [
        (1, "ReportLine(coverage=1)"),
        (2, "ReportLine(coverage=2)"),
        (3, "ReportLine(coverage=3)"),
        (4, "ReportLine(coverage=4)"),
        (5, "ReportLine(coverage=5)"),
        (6, "ReportLine(coverage=6)"),
        (7, "ReportLine(coverage=7)"),
        (8, "ReportLine(coverage=8)"),
        (9, "ReportLine(coverage=9)"),
    ]


@pytest.mark.unit
def test_del_item():
    r = ReportFile("name.h")
    with pytest.raises(TypeError):
        del r["line"]
    with pytest.raises(ValueError):
        del r[-1]
