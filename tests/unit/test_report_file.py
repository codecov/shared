import pytest

from shared.reports.resources import ReportFile
from shared.reports.types import ReportLine, ReportTotals


@pytest.mark.unit
def test_eof():
    r = ReportFile("filename")
    r._lines = [ReportLine.create(1), ReportLine.create(2)]
    assert r.eof == 3


@pytest.mark.unit
def test_len():
    r = ReportFile("filename")
    r._lines = [ReportLine.create(1), ReportLine.create(2), None]
    assert len(r) == 2


@pytest.mark.unit
def test_repr():
    r = ReportFile("filename")
    r._lines = [ReportLine.create(1), ReportLine.create(2), None]
    r.name = "name.py"
    assert repr(r) == "<ReportFile name=name.py lines=2>"


@pytest.mark.unit
def test_lines():
    r = ReportFile("filename")
    r._lines = [ReportLine.create(1), ReportLine.create(2), None]
    assert list(r.lines) == [(1, ReportLine.create(1)), (2, ReportLine.create(2))]


@pytest.mark.unit
def test_iter():
    r = ReportFile("filename")
    r._lines = [ReportLine.create(1), ReportLine.create(2), None]
    lines = [ln for ln in r]
    assert lines == [ReportLine.create(1), ReportLine.create(2), None]


@pytest.mark.unit
def test_get_item():
    r = ReportFile("filename")
    r._lines = [
        ReportLine.create(1),
        ReportLine.create(2),
        ReportLine.create(3),
        ReportLine.create(4),
    ]
    r._totals = ReportTotals(0, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0)
    assert r[1] == ReportLine.create(1)
    assert r["totals"] == ReportTotals(0, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0)


@pytest.mark.unit
@pytest.mark.parametrize(
    "get_val, error_message",
    [
        ([], "expecting type int got <class 'list'>"),
        (-1, "Line number must be greater then 0. Got -1"),
        (1, "Line #1 not found in report"),
    ],
)
def test_get_item_exception(get_val, error_message):
    r = ReportFile("filename")
    r._lines = []
    with pytest.raises(Exception) as e_info:
        r[get_val]
    assert str(e_info.value) == error_message


@pytest.mark.unit
@pytest.mark.parametrize(
    "index, set_val, error_message",
    [
        ("str", 1, "expecting type int got <class 'str'>"),
        (1, "str", "expecting type ReportLine got <class 'str'>"),
        (-1, ReportLine.create(), "Line number must be greater then 0. Got -1"),
    ],
)
def test_set_item_exception(index, set_val, error_message):
    r = ReportFile("filename")
    with pytest.raises(Exception) as e_info:
        r[index] = set_val
    assert str(e_info.value) == error_message


@pytest.mark.unit
def test_get_slice():
    r = ReportFile("filename")
    r._lines = [
        ReportLine.create(1),
        ReportLine.create(2),
        ReportLine.create(3),
        ReportLine.create(4),
    ]
    assert list(r[2:4]) == [
        (2, ReportLine.create(2)),
        (3, ReportLine.create(3)),
    ]


@pytest.mark.unit
def test_contains():
    r = ReportFile("filename")
    r._lines = [
        ReportLine.create(1),
        ReportLine.create(2),
        ReportLine.create(3),
        ReportLine.create(4),
    ]
    assert (1 in r) is True
    assert (10 in r) is False


@pytest.mark.unit
def test_contains_exception():
    r = ReportFile("filename")
    with pytest.raises(Exception) as e_info:
        "str" in r
    assert str(e_info.value) == "expecting type int got <class 'str'>"


@pytest.mark.unit
@pytest.mark.parametrize(
    "totals, boolean", [(ReportTotals(), False), (ReportTotals(1, 1, 1, 1), True)]
)
def test_non_zero(totals, boolean):
    r = ReportFile("filename")
    r._totals = totals
    assert bool(r) is boolean


@pytest.mark.unit
def test_get():
    r = ReportFile("filename")
    r._lines = [
        ReportLine.create(1),
        ReportLine.create(2),
        ReportLine.create(3),
        ReportLine.create(4),
    ]
    assert r.get(1) == ReportLine.create(1)


@pytest.mark.unit
@pytest.mark.parametrize(
    "get_val, error_message",
    [
        ("str", "expecting type int got <class 'str'>"),
        (-1, "Line number must be greater then 0. Got -1"),
    ],
)
def test_report_file_get_exception(get_val, error_message):
    r = ReportFile("filename")
    with pytest.raises(Exception) as e_info:
        r.get(get_val)
    assert str(e_info.value) == error_message


@pytest.mark.unit
@pytest.mark.parametrize(
    "key, val, error_message",
    [
        ("str", ReportLine.create(), "expecting type int got <class 'str'>"),
        (1, "str", "expecting type ReportLine got <class 'str'>"),
        (-1, ReportLine.create(), "Line number must be greater then 0. Got -1"),
    ],
)
def test_report_file_append_exception(key, val, error_message):
    r = ReportFile("filename")
    with pytest.raises(Exception) as e_info:
        r.append(key, val)
    assert str(e_info.value) == error_message


@pytest.mark.unit
@pytest.mark.parametrize(
    "name, totals, list_before, merge_val, merge_return, list_after",
    [
        ("file.py", None, [], None, None, []),
        (
            "file.rb",
            None,
            [],
            ReportFile(name="file.rb", lines=[ReportLine.create(2)]),
            True,
            [(1, ReportLine.create(2))],
        ),
    ],
)
def test_merge(name, totals, list_before, merge_val, merge_return, list_after):
    r = ReportFile("filename")
    r.name = name
    r._lines = []
    r._totals = totals
    assert list(r.lines) == list_before
    assert r.merge(merge_val) == merge_return
    assert list(r.lines) == list_after


@pytest.mark.unit
@pytest.mark.parametrize(
    "_process_totals_return_val, _totals, is_process_called, totals",
    [
        (ReportTotals(1), None, True, ReportTotals(1)),
        (ReportTotals(2), ReportTotals(1), False, ReportTotals(1)),
    ],
)
def test_totals(_process_totals_return_val, _totals, is_process_called, totals, mocker):
    mocker.patch.object(
        ReportFile, "_process_totals", return_value=_process_totals_return_val
    )
    r = ReportFile("filename")
    r._totals = _totals
    assert r.totals == totals
    assert ReportFile._process_totals.called is is_process_called


@pytest.mark.unit
@pytest.mark.parametrize(
    "lines, diff, new_file, boolean",
    [
        ([], {"segments": []}, ReportFile("new.py"), False),
        (
            [],
            {
                "segments": [
                    {"header": [1, 1, 1, 1], "lines": ["- afefe", "+ fefe", "="]}
                ]
            },
            ReportFile("new.py"),
            False,
        ),
        (
            [ReportLine.create(1), ReportLine.create(2)],
            {
                "segments": [
                    {"header": [1, 1, 1, 1], "lines": ["- afefe", "+ fefe", "="]}
                ]
            },
            ReportFile("new.py"),
            True,
        ),
        (
            [],
            {
                "segments": [
                    {"header": [1, 1, 1, 1], "lines": ["- afefe", "+ fefe", "="]}
                ]
            },
            ReportFile("new.py", lines=[ReportLine.create(1), ReportLine.create(2)]),
            True,
        ),
    ],
)
def test_does_diff_adjust_tracked_lines(lines, diff, new_file, boolean):
    r = ReportFile("filename")
    r._lines = lines
    assert r.does_diff_adjust_tracked_lines(diff, new_file) is boolean


@pytest.mark.unit
def test_shift_lines_by_diff():
    r = ReportFile("filename")
    r._lines = [ReportLine.create(), ReportLine.create()]
    assert len(list(r.lines)) == 2
    r.shift_lines_by_diff(
        {
            "segments": [
                {
                    # [-, -, POS_to_start, new_lines_added]
                    "header": [1, 1, 1, 1],
                    "lines": ["- afefe", "+ fefe", "="],
                }
            ]
        }
    )
    assert len(list(r.lines)) == 1


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
