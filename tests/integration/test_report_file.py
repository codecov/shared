import pytest

from shared.reports.resources import ReportFile
from shared.reports.types import ReportLine, ReportTotals


@pytest.mark.integration
def test_report_file_constructor():
    r1 = ReportFile("folder/file.py", [0, 1, 1, 1])
    assert r1.name == "folder/file.py"
    r2 = ReportFile(name="file.py", lines="\n[1,2]\n[1,1]")
    assert list(r2.lines) == [
        (1, ReportLine.create(1, 2)),
        (2, ReportLine.create(1, 1)),
    ]
    assert r2.name == "file.py"


@pytest.mark.integration
def test_repr():
    r = ReportFile("folder/file.py", [0, 1, 1, 1])
    assert repr(r) == "<ReportFile name=folder/file.py lines=0>"


@pytest.mark.integration
@pytest.mark.parametrize(
    "r, get_val, res",
    [
        (
            ReportFile("folder/file.py", [0, 1, 1, 1]),
            "totals",
            ReportTotals(0, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0),
        ),
        (
            ReportFile("file.py", lines=[ReportLine.create(), ReportLine.create()]),
            1,
            ReportLine.create(),
        ),
    ],
)
def test_get_item(r, get_val, res):
    assert r[get_val] == res


@pytest.mark.integration
@pytest.mark.parametrize(
    "get_val, error_message",
    [
        ([], "expecting type int got <class 'list'>"),
        (-1, "Line number must be greater then 0. Got -1"),
        (1, "Line #1 not found in report"),
    ],
)
def test_get_item_exception(get_val, error_message):
    r = ReportFile("folder/file.py", [0, 1, 1, 1])
    with pytest.raises(Exception) as e_info:
        r[get_val]
    assert str(e_info.value) == error_message


@pytest.mark.integration
@pytest.mark.parametrize(
    "r, get_val",
    [
        (
            ReportFile(
                name="folder/file.py",
                lines=[ReportLine.create(1)],
                ignore={"eof": "N", "lines": [1, 10]},
            ),
            ReportLine.create(1),
        ),
        (
            ReportFile(name="folder/file.py", lines=[ReportLine.create(1)]),
            ReportLine.create(0),
        ),
    ],
)
def test_set_item(r, get_val):
    assert r[1] == ReportLine.create(1)
    r[1] = ReportLine.create(0)
    assert r[1] == get_val


def test_set_item_with_ignore_lines():
    ignore_lines = {"eof": 41, "lines": {40, 33, 37, 38}}
    filename = "folder/file.java"
    r = ReportFile(filename, ignore=ignore_lines)
    r[1] = ReportLine.create(0)
    r[2] = ReportLine.create(1)
    r[33] = ReportLine.create(0)
    r[37] = ReportLine.create("1/2")
    r[38] = ReportLine.create(1)
    r[39] = ReportLine.create("2/3")
    r[40] = ReportLine.create(0)
    r[41] = ReportLine.create(1)
    r[42] = ReportLine.create("1/8")
    assert list(r.lines) == [
        (1, ReportLine.create(0)),
        (2, ReportLine.create(1)),
        (39, ReportLine.create("2/3")),
        (41, ReportLine.create(1)),
    ]


@pytest.mark.integration
@pytest.mark.parametrize(
    "index, set_val, error_message",
    [
        ("str", 1, "expecting type int got <class 'str'>"),
        (1, "str", "expecting type ReportLine got <class 'str'>"),
        (-1, ReportLine.create(), "Line number must be greater then 0. Got -1"),
    ],
)
def test_set_item_exception(index, set_val, error_message):
    r = ReportFile("folder/file.py")
    with pytest.raises(Exception) as e_info:
        r[index] = set_val
    assert str(e_info.value) == error_message


@pytest.mark.integration
def test_len():
    r = ReportFile(
        name="folder/file.py", lines=[ReportLine.create(1), ReportLine.create(), None]
    )
    assert len(r) == 2


@pytest.mark.integration
def test_eol():
    r = ReportFile(
        name="folder/file.py", lines=[ReportLine.create(1), ReportLine.create(), None]
    )
    assert r.eof == 4


@pytest.mark.integration
def test_get_slice():
    r = ReportFile(
        name="folder/file.py",
        lines=[
            ReportLine.create(1),
            ReportLine.create(2),
            ReportLine.create(3),
            ReportLine.create(4),
        ],
    )
    assert list(r[2:4]) == [
        (2, ReportLine.create(2)),
        (3, ReportLine.create(3)),
    ]


@pytest.mark.integration
@pytest.mark.parametrize(
    "r, boolean",
    [
        (ReportFile(name="name.py"), False),
        (ReportFile(name="name.py", lines=[ReportLine.create(1)]), True),
    ],
)
def test_non_zero(r, boolean):
    assert bool(r) is boolean


@pytest.mark.integration
def test_contains():
    r = ReportFile("file.py", lines=[ReportLine.create(1), ReportLine.create(2)])
    assert (2 in r) is True
    assert (7 in r) is False


@pytest.mark.integration
def test_contains_exception():
    r = ReportFile("folder/file.py")
    with pytest.raises(Exception) as e_info:
        "str" in r
    assert str(e_info.value) == "expecting type int got <class 'str'>"


@pytest.mark.integration
def test_report_file_get():
    r = ReportFile(
        name="folder/file.py", lines=[ReportLine.create(), ReportLine.create()]
    )
    assert r.get(1) == ReportLine.create()


@pytest.mark.integration
@pytest.mark.parametrize(
    "get_val, error_message",
    [
        ("str", "expecting type int got <class 'str'>"),
        (-1, "Line number must be greater then 0. Got -1"),
    ],
)
def test_report_file_get_exception(get_val, error_message):
    r = ReportFile("folder/file.py")
    with pytest.raises(Exception) as e_info:
        r.get(get_val)
    assert str(e_info.value) == error_message


# TODO branch where this calls merge_line
@pytest.mark.integration
@pytest.mark.parametrize(
    "r, boolean, lines",
    [
        (
            ReportFile(name="folder/file.py", ignore={"eof": "N", "lines": [1, 10]}),
            False,
            [],
        ),
        (ReportFile(name="file.py"), True, [(1, ReportLine.create(1))]),
    ],
)
def test_append(r, boolean, lines):
    assert r.append(1, ReportLine.create(1)) is boolean
    assert list(r.lines) == lines


@pytest.mark.integration
@pytest.mark.parametrize(
    "key, val, error_message",
    [
        ("str", ReportLine.create(), "expecting type int got <class 'str'>"),
        (1, "str", "expecting type ReportLine got <class 'str'>"),
        (-1, ReportLine.create(), "Line number must be greater then 0. Got -1"),
    ],
)
def test_report_file_append_exception(key, val, error_message):
    r = ReportFile("folder/file.py")
    with pytest.raises(Exception) as e_info:
        r.append(key, val)
    assert str(e_info.value) == error_message


# TODO branch where merge_line is called
@pytest.mark.integration
@pytest.mark.parametrize(
    "r, list_before, merge_val, merge_return, list_after",
    [
        (ReportFile(name="file.py"), [], None, None, []),
        (
            ReportFile(name="file.rb"),
            [],
            ReportFile(name="file.rb", lines=[ReportLine.create(2)]),
            True,
            [(1, ReportLine.create(2))],
        ),
        (
            ReportFile(name="file.rb", totals=[1, 2, 3]),
            [],
            ReportFile(name="file.rb"),
            False,
            [],
        ),
    ],
)
def test_merge(r, list_before, merge_val, merge_return, list_after):
    assert list(r.lines) == list_before
    assert r.merge(merge_val) == merge_return
    assert list(r.lines) == list_after


@pytest.mark.integration
def test_merge_exception():
    r = ReportFile(name="name.py")
    with pytest.raises(Exception) as e_info:
        r.merge("str")
    assert str(e_info.value) == "expecting type ReportFile got <class 'str'>"


@pytest.mark.integration
def test_totals():
    r = ReportFile(name="file.py", totals=[0])
    assert r.totals == ReportTotals(0)


@pytest.mark.integration
def test_report_file_lines():
    r = ReportFile(name="asd", lines=[[1]])
    assert list(r.lines) == [(1, ReportLine.create(1))]


@pytest.mark.integration
def test_report_iter():
    r = ReportFile(
        name="folder/file.py",
        lines=[ReportLine.create(coverage=1), ReportLine.create(coverage=0)],
    )
    lines = [ln for ln in r]
    assert lines == [ReportLine.create(coverage=1), ReportLine.create(coverage=0)]


@pytest.mark.integration
@pytest.mark.parametrize(
    "r, diff, new_file, boolean",
    [
        (ReportFile("file.py"), {"segments": []}, ReportFile("new.py"), False),
        (
            ReportFile("file.py"),
            {
                "segments": [
                    {"header": [1, 1, 1, 1], "lines": ["- afefe", "+ fefe", "="]}
                ]
            },
            ReportFile("new.py"),
            False,
        ),
        (
            ReportFile("file.py", lines=[ReportLine.create(1), ReportLine.create(2)]),
            {
                "segments": [
                    {"header": [1, 1, 1, 1], "lines": ["- afefe", "+ fefe", "="]}
                ]
            },
            ReportFile("new.py"),
            True,
        ),
        (
            ReportFile("file.py"),
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
def test_does_diff_adjust_tracked_lines(r, diff, new_file, boolean):
    assert r.does_diff_adjust_tracked_lines(diff, new_file) is boolean


@pytest.mark.integration
def test_shift_lines_by_diff():
    r = ReportFile(
        name="folder/file.py", lines=[ReportLine.create(), ReportLine.create()]
    )
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


@pytest.mark.integration
@pytest.mark.parametrize(
    "r, encoded_val",
    [
        (ReportFile("name.py"), "{}\n"),
        (
            ReportFile("name.py", lines=[ReportLine.create(1), ReportLine.create(2)]),
            "null\n[1]\n[2]",
        ),
    ],
)
def test_encode(r, encoded_val):
    assert r._encode() == encoded_val
