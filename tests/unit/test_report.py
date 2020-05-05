import pytest
from mock import PropertyMock

from shared.reports.resources import Report, ReportFile, _encode_chunk
from shared.utils.match import match
from shared.utils.sessions import Session
from shared.reports.types import ReportLine, ReportTotals, NetworkFile, LineSession
from tests.helper import v2_to_v3

END_OF_CHUNK = "\n<<<<< end_of_chunk >>>>>\n"


@pytest.mark.unit
def test_report_repr(patch):
    patch.init(Report)
    r = Report()
    r._files = []
    assert repr(Report()) == "<Report files=0>"


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
                    NetworkFile(
                        totals=ReportTotals(1), session_totals=None, diff_totals=None
                    ),
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
                        session_totals=None,
                        diff_totals=None,
                    ),
                )
            ],
        ),
    ],
)
def test_network(files, mocker, chunks, path_filter, network, patch):
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
def test_files(files, path_filter, patch):
    r = Report(files=files)
    r._path_filter = path_filter
    assert r.files == ["py.py"]


@pytest.mark.unit
def test_resolve_paths(patch):
    r = Report(files={"py.py": [0, ReportTotals(1)]})
    r._path_filter = None
    r._chunks = "null\n[1]\n[1]\n[1]\n<<<<< end_of_chunk >>>>>\nnull\n[1]\n[1]\n[1]".split(
        END_OF_CHUNK
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
            ReportFile("a", totals=ReportTotals(1, 50, 10), lines=[ReportLine(1)]),
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
def test_append_error(patch):
    patch.init(Report)
    r = Report()
    with pytest.raises(Exception) as e_info:
        r.append("str")
    assert str(e_info.value) == "expecting ReportFile got <class 'str'>"


@pytest.mark.unit
@pytest.mark.parametrize(
    "files, chunks, path_filter, file_repr, lines",
    [
        (
            {"file.py": [0, ReportTotals(1)]},
            None,
            None,
            "<ReportFile name=file.py lines=0>",
            [],
        ),
        ({"py.py": [0, ReportTotals(1)]}, None, None, "None", None),
        (
            {"file.py": [0, ReportTotals(1)]},
            None,
            lambda filename: match(["py.py"], filename),
            "None",
            None,
        ),
        (
            {"file.py": [0, ReportTotals(1)]},
            "null\n[1]\n[1]\n[1]\n<<<<< end_of_chunk >>>>>\nnull\n[1]\n[1]\n[1]".split(
                END_OF_CHUNK
            ),
            None,
            "<ReportFile name=file.py lines=3>",
            [(1, ReportLine(1)), (2, ReportLine(1)), (3, ReportLine(1))],
        ),
        (
            {"file.py": [0, ReportTotals(1)]},
            [ReportFile(name="file.py")],
            None,
            "<ReportFile name=file.py lines=0>",
            [],
        ),
        (
            {"file.py": [1, ReportTotals(1)]},
            [ReportFile(name="other-file.py")],
            None,
            "<ReportFile name=file.py lines=0>",
            [],
        ),
    ],
)
def test_get(files, chunks, path_filter, file_repr, lines, patch):
    r = Report(files=files)
    r._chunks = chunks
    r._path_filter = path_filter
    r._line_modifier = None

    assert repr(r.get("file.py")) == file_repr
    if lines:
        assert list(r.get("file.py").lines) == lines


@pytest.mark.unit
def test_rename(patch):
    r = Report(files={"file.py": [0, ReportTotals(1)]})
    r._path_filter = None
    r._line_modifier = None
    r._chunks = "null\n[1]\n[1]\n[1]\n<<<<< end_of_chunk >>>>>\nnull\n[1]\n[1]\n[1]".split(
        END_OF_CHUNK
    )
    assert r.get("name.py") is None
    assert repr(r.get("file.py")) == "<ReportFile name=file.py lines=3>"
    assert r.rename("file.py", "name.py") is True
    assert r.get("file.py") is None
    assert repr(r.get("name.py")) == "<ReportFile name=name.py lines=3>"


@pytest.mark.unit
def test_get_item(patch):
    patch.init(Report)
    r = Report()
    r._files = PropertyMock(return_value={"file.py": [0, ReportTotals(1)]})
    r._chunks = None
    r._path_filter = None
    r._line_modifier = None
    assert repr(r["file.py"]) == "<ReportFile name=file.py lines=0>"


@pytest.mark.unit
def test_get_item_exception(patch):
    patch.init(Report)
    r = Report()
    r._files = {"file.py": [0, ReportTotals(1)]}
    r._path_filter = None
    r._line_modifier = None
    r._chunks = None
    with pytest.raises(Exception) as e_info:
        r["name.py"]
    assert str(e_info.value) == "File at path name.py not found in report"


@pytest.mark.unit
def test_del_item(patch):
    r = Report(files={"file.py": [0, ReportTotals(1)]})
    r._path_filter = None
    r._line_modifier = None
    r._chunks = "null\n[1]\n[1]\n[1]\n<<<<< end_of_chunk >>>>>\nnull\n[1]\n[1]\n[1]".split(
        END_OF_CHUNK
    )
    assert repr(r.get("file.py")) == "<ReportFile name=file.py lines=3>"
    del r["file.py"]
    assert r.get("file.py") is None


@pytest.mark.unit
@pytest.mark.parametrize(
    "files, path_filter, manifest",
    [
        (
            {"file1.py": [0, ReportTotals(1)], "file2.py": [1, ReportTotals(1)]},
            None,
            ["file1.py", "file2.py"],
        ),
        (
            {"file1.py": [0, ReportTotals(1)], "file2.py": [1, ReportTotals(1)]},
            lambda filename: match(["file2.py"], filename),
            ["file2.py"],
        ),
    ],
)
def test_manifest(files, path_filter, manifest, patch):
    patch.init(Report)
    r = Report()
    r._files = files
    r._chunks = None
    r._path_filter = path_filter
    r._line_modifier = None
    assert r.manifest == manifest


@pytest.mark.unit
def test_get_folder_totals(patch):
    r = Report(
        files={
            "path/file1.py": [0, ReportTotals(1)],
            "path/file2.py": [0, ReportTotals(1)],
            "wrong/path/file2.py": [0, ReportTotals(1)],
        }
    )
    r._chunks = [
        ReportFile(name="path/file1.py", totals=[1, 2, 1]),
        ReportFile(name="path/file2.py", totals=[1, 2, 1]),
    ]
    r._path_filter = None
    r._line_modifier = None
    assert r.get_folder_totals("/path/") == ReportTotals(
        files=2, lines=4, hits=2, misses=0, partials=0, coverage="50.00000"
    )


@pytest.mark.unit
def test_flags(patch):
    patch.init(Report)
    r = Report()
    r._files = {"py.py": [0, ReportTotals(1)]}
    r._chunks = None
    r._path_filter = None
    r._line_modifier = None
    r.sessions = {1: Session(flags={"a": 1, 1: 1, "test": 1})}
    assert list(r.flags.keys()) == ["a", 1, "test"]


@pytest.mark.unit
def test_iter(patch):
    r = Report(
        files={"file1.py": [0, ReportTotals(1)], "file2.py": [1, ReportTotals(1)],}
    )
    r._chunks = None
    r._path_filter = None
    r._line_modifier = None
    files = []
    for _file in r:
        files.append(_file)
    assert (
        repr(files)
        == "[<ReportFile name=file1.py lines=0>, <ReportFile name=file2.py lines=0>]"
    )


@pytest.mark.unit
def test_contains(patch):
    patch.init(Report)
    r = Report()
    r._files = {
        "file1.py": [0, ReportTotals(1)],
    }
    assert ("file1.py" in r) is True
    assert ("file2.py" in r) is False


@pytest.mark.unit
@pytest.mark.parametrize(
    "files, chunks, new_report, manifest",
    [
        ({"file.py": [0, ReportTotals(1)],}, None, None, ["file.py"]),
        ({"file.py": [0, ReportTotals(1)],}, None, Report(), ["file.py"]),
        (
            {"file.py": [0, ReportTotals(1)],},
            "null\n[1]\n[1]\n[1]\n<<<<< end_of_chunk >>>>>".split(END_OF_CHUNK),
            Report(
                files={"other-file.py": [1, ReportTotals(2)]},
                chunks="null\n[1]\n[1]\n[1]\n<<<<< end_of_chunk >>>>>\nnull\n[1]\n[1]\n[1]",
            ),
            ["file.py", "other-file.py"],
        ),
    ],
)
def test_merge(files, chunks, new_report, manifest, patch):
    r = Report(files=files)
    r._chunks = chunks
    r._path_filter = None
    r._line_modifier = None
    r.sessions = {}
    r._filter_cache = (None, None)
    assert r.manifest == ["file.py"]
    r.merge(new_report)
    assert r.manifest == manifest


@pytest.mark.unit
@pytest.mark.parametrize(
    "files, path_filter, boolean",
    [
        ({}, None, True),
        (
            {"file.py": [0, ReportTotals(1)]},
            lambda filename: match(["this-file.py"], filename),
            True,
        ),
        ({"file.py": [0, ReportTotals(1)]}, None, False),
    ],
)
def test_is_empty(files, path_filter, boolean, patch):
    patch.init(Report)
    r = Report()
    r._files = files
    r._chunks = None
    r._path_filter = path_filter
    assert r.is_empty() is boolean


@pytest.mark.unit
@pytest.mark.parametrize(
    "files, boolean", [({}, False), ({"file.py": [0, ReportTotals(1)]}, True),]
)
def test_non_zero(files, boolean, patch):
    patch.init(Report)
    r = Report()
    r._files = files
    r._chunks = None
    r._path_filter = None
    assert bool(r) is boolean


@pytest.mark.unit
def test_to_archive(patch):
    patch.init(Report)
    r = Report()
    r._files = PropertyMock(return_value={"file.py": [0, ReportTotals()]})
    r._chunks = "null\n[1]\n[1]\n[1]\n<<<<< end_of_chunk >>>>>\nnull\n[1]\n[1]\n[1]".split(
        END_OF_CHUNK
    )
    assert (
        r.to_archive()
        == "null\n[1]\n[1]\n[1]\n<<<<< end_of_chunk >>>>>\nnull\n[1]\n[1]\n[1]"
    )


@pytest.mark.unit
def test_to_database(patch):
    r = Report(files={"file.py": [0, ReportTotals()]})
    r._chunks = "null\n[1]\n[1]\n[1]\n<<<<< end_of_chunk >>>>>\nnull\n[1]\n[1]\n[1]".split(
        END_OF_CHUNK
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
            "c": "100",
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
        '{"files": {"file.py": [0, [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], null, null]}, "sessions": {}}',
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
def test_does_diff_adjust_tracked_lines(diff, future, future_diff, res, patch):
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
def test_apply_diff_no_append(patch):
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
def test_report_has_flag(patch):
    patch.init(Report)
    r = Report()
    r.sessions = {1: Session(flags=["a"])}
    assert r.has_flag("a")
    assert not r.has_flag("b")


@pytest.mark.unit
def test_add_session(patch):
    patch.init(Report)
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
def test_flare(files, chunks, params, flare, patch):
    r = Report(files=files)
    r._chunks = chunks
    r._path_filter = None
    r._line_modifier = None
    assert r.flare(**params) == flare


# TODO see filter method on Report(), method does nothing because self.reset() is called after _filter_cache is set
# @pytest.mark.unit
# def test_filter():
#     r = Report().filter(paths=['test/path/file.py'])
#     assert r.get('wrong/test/path/file.py') is None
#
#     r1 = Report(files={
#         'file.py':[0, ReportTotals(1)]
#     }, chunks='null\n[1]\n[1]\n[1]\n<<<<< end_of_chunk >>>>>\nnull\n[1]\n[1]\n[1]').filter(flags='test')


def test_test(patch):
    patch.init(ReportFile)
    patch.object(ReportFile, "ignore_lines", return_value=None)
    r = Report(files={"py.py": [0, ReportTotals(1)]})
    r._chunks = "null\n[1]\n[1]\n[1]\n<<<<< end_of_chunk >>>>>\nnull\n[1]\n[1]\n[1]".split(
        END_OF_CHUNK
    )
    r._path_filter = None
    r._line_modifier = None
    r.ignore_lines({"py.py": {"lines": [0, 1, 2]}})
    assert ReportFile.ignore_lines.called is True


@pytest.mark.unit
def test_filter_exception(patch):
    patch.init(Report)
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
            [ReportLine(2), ReportLine(1)],
            "[[2,null,null,null,null],[1,null,null,null,null]]",
        ),
    ],
)
def test_encode_chunk(chunk, res):
    assert _encode_chunk(chunk) == res


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
        ReportLine(coverage="1/2", sessions=[LineSession(0, "1/2"), LineSession(1, 0)]),
        ReportLine(coverage="1/2", sessions=[LineSession(0, 0), LineSession(1, "1/2")]),
    ]
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
        (1, ReportLine(coverage=1, sessions=[LineSession(0, 1)])),
        (4, ReportLine(coverage=0, sessions=[LineSession(0, 0)])),
        (5, ReportLine(coverage=1, sessions=[LineSession(0, 1)])),
        (6, ReportLine(coverage=0, sessions=[LineSession(0, 0)])),
        (9, ReportLine(coverage=1, sessions=[LineSession(0, 1)])),
        (10, ReportLine(coverage="1/2", sessions=[LineSession(0, "1/2")])),
        (13, ReportLine(coverage=1, sessions=[LineSession(0, 1)])),
        (15, ReportLine(coverage="1/2", sessions=[LineSession(0, "1/2")])),
        (16, ReportLine(coverage=0, sessions=[LineSession(0, 0)])),
    ]
    assert list(report_file.lines) == expected_result
    assert report_file.get(1) == ReportLine(coverage=1, sessions=[LineSession(0, 1)])
    assert report_file.get(13) == ReportLine(coverage=1, sessions=[LineSession(0, 1)])
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
