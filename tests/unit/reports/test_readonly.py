from pathlib import Path

import pytest

from shared.reports.readonly import LazyRustReport, ReadOnlyReport
from shared.reports.resources import ReportFile
from shared.reports.types import LineSession, ReportLine, ReportTotals
from shared.utils.sessions import Session, SessionType

current_file = Path(__file__)


@pytest.fixture
def sample_rust_report(mocker):
    mocker.patch.object(ReadOnlyReport, "should_load_rust_version", return_value=True)
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
    return ReadOnlyReport.from_chunks(
        chunks=chunks, files=files_dict, sessions=sessions_dict
    )


class TestLazyRustReport(object):
    def test_get_report(self):
        with open(current_file.parent / "samples" / "chunks_01.txt", "r") as f:
            chunks = f.read()
        filename_mapping = {
            "awesome/__init__.py": 2,
            "tests/__init__.py": 0,
            "tests/test_sample.py": 1,
        }
        session_mapping = {0: ["unit"]}
        r = LazyRustReport(filename_mapping, chunks, session_mapping)
        assert r is not None
        assert r.get_report() is not None

    def test_get_report_is_lazy_loaded(self, mocker):
        mocker.patch(
            "shared.reports.readonly.metrics.timer",
            return_value=mocker.MagicMock(
                ms=10000,
                __enter__=mocker.MagicMock(return_value=mocker.MagicMock(ms=10000)),
            ),
        )
        with open(current_file.parent / "samples" / "chunks_01.txt", "r") as f:
            chunks = f.read()
        filename_mapping = {
            "awesome/__init__.py": 2,
            "tests/__init__.py": 0,
            "tests/test_sample.py": 1,
        }
        session_mapping = {0: ["unit"]}
        r = LazyRustReport(filename_mapping, chunks, session_mapping)
        assert r is not None
        assert r.get_report() is not None

    def test_get_report_took_too_long(self):
        with open(current_file.parent / "samples" / "chunks_01.txt", "r") as f:
            chunks = f.read()
        filename_mapping = {
            "awesome/__init__.py": 2,
            "tests/__init__.py": 0,
            "tests/test_sample.py": 1,
        }
        session_mapping = {0: ["unit"]}
        r = LazyRustReport(filename_mapping, chunks, session_mapping)
        assert r is not None
        assert r.get_report() is not None


class TestReadOnly(object):
    def test_create_from_report(self, sample_report, mocker):
        mocker.patch.object(
            ReadOnlyReport, "should_load_rust_version", return_value=True
        )
        r = ReadOnlyReport.create_from_report(sample_report)
        assert r.rust_report is not None
        assert r.totals == sample_report.totals
        assert r.sessions[0] == sample_report.sessions[0]
        assert r.sessions == sample_report.sessions
        assert sorted(r.flags.keys()) == ["complex", "simple"]
        assert r.flags["complex"].totals.asdict() == {
            "files": 2,
            "lines": 6,
            "hits": 2,
            "misses": 2,
            "partials": 2,
            "coverage": "33.33333",
            "branches": 1,
            "methods": 0,
            "messages": 0,
            "sessions": 2,
            "complexity": 0,
            "complexity_total": 0,
            "diff": 0,
        }
        assert r.apply_diff(
            {
                "files": {
                    "file_1.go": {
                        "type": "modified",
                        "segments": [{"header": list("1313"), "lines": list("---+++")}],
                    },
                    "location/file_1.py": {
                        "type": "modified",
                        "segments": [
                            {
                                "header": ["100", "3", "100", "3"],
                                "lines": list("-+-+-+"),
                            }
                        ],
                    },
                    "deleted.py": {"type": "deleted"},
                }
            }
        ).asdict() == {
            "branches": 2,
            "complexity": 0,
            "complexity_total": 0,
            "coverage": "60.00000",
            "diff": 0,
            "files": 2,
            "hits": 3,
            "lines": 5,
            "messages": 0,
            "methods": 0,
            "misses": 0,
            "partials": 2,
            "sessions": 0,
        }
        res = r.calculate_diff(
            {
                "files": {
                    "file_1.go": {
                        "type": "modified",
                        "segments": [{"header": list("1313"), "lines": list("---+++")}],
                    },
                    "location/file_1.py": {
                        "type": "modified",
                        "segments": [
                            {
                                "header": ["100", "3", "100", "3"],
                                "lines": list("-+-+-+"),
                            }
                        ],
                    },
                    "deleted.py": {"type": "deleted"},
                }
            }
        )
        assert res["general"].asdict() == dict(
            files=2,
            lines=5,
            hits=3,
            misses=0,
            partials=2,
            coverage="60.00000",
            branches=2,
            methods=0,
            messages=0,
            sessions=0,
            complexity=0,
            complexity_total=0,
            diff=0,
        )
        assert res["files"]["location/file_1.py"].asdict() == dict(
            files=0,
            lines=2,
            hits=0,
            misses=0,
            partials=2,
            coverage="0",
            branches=2,
            methods=0,
            messages=0,
            sessions=0,
            complexity=0,
            complexity_total=0,
            diff=0,
        )
        assert res["files"]["file_1.go"].asdict() == dict(
            files=0,
            lines=3,
            hits=3,
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
        )

    def test_get_file_totals(self, sample_report, mocker):
        r = ReadOnlyReport.create_from_report(sample_report)
        print(sample_report._files)
        print(r)
        assert r.get_file_totals("location/file_1.py") == ReportTotals(
            files=0,
            lines=2,
            hits=0,
            misses=0,
            partials=2,
            coverage="0",
            branches=2,
            methods=0,
            messages=0,
            sessions=0,
            complexity=0,
            complexity_total=0,
            diff=0,
        )

    def test_from_chunks_with_totals(self, mocker):
        mocked_process_totals = mocker.patch.object(ReadOnlyReport, "_process_totals")
        mocker.patch.object(
            ReadOnlyReport, "should_load_rust_version", return_value=True
        )
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
        r = ReadOnlyReport.from_chunks(
            chunks=chunks,
            files=files_dict,
            sessions=sessions_dict,
            totals={
                "f": 3,
                "n": 20,
                "h": 17,
                "m": 3,
                "p": 0,
                "c": "85.00000",
                "b": 0,
                "d": 0,
                "M": 0,
                "s": 1,
                "C": 0,
                "N": 0,
            },
        )
        assert r._totals == ReportTotals(
            files=3,
            lines=20,
            hits=17,
            misses=3,
            partials=0,
            coverage="85.00000",
            branches=0,
            methods=0,
            messages=0,
            sessions=1,
            complexity=0,
            complexity_total=0,
            diff=0,
        )
        assert r.totals == r._totals
        assert not mocked_process_totals.called

    def test_filter_totals(self, sample_report):
        r = ReadOnlyReport.create_from_report(sample_report)
        assert r.filter(paths=[".*.go"]).totals.asdict() == {
            "files": 2,
            "lines": 7,
            "hits": 4,
            "misses": 1,
            "partials": 2,
            "coverage": "57.14286",
            "branches": 1,
            "methods": 0,
            "messages": 0,
            "sessions": 4,
            "complexity": 0,
            "complexity_total": 0,
            "diff": 0,
        }

    def test_filter_none(self, sample_rust_report):
        assert sample_rust_report.rust_report is not None
        assert sample_rust_report.rust_report.get_report() is not None
        assert sample_rust_report.filter() is sample_rust_report

    def test_init_no_loading_rust(self, mocker):
        chunks = "\n".join(
            ["{}", "", "", "[1, null, [[0, 1], [1, 0]]]", "[0, null, [[0, 0], [1, 0]]]"]
        )
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
        mocker.patch.object(
            ReadOnlyReport, "should_load_rust_version", return_value=False
        )
        r = ReadOnlyReport.from_chunks(
            chunks=chunks, files=files_dict, sessions=sessions_dict
        )
        assert r.rust_report is None
        assert r.totals == ReportTotals(
            files=3,
            lines=20,
            hits=17,
            misses=3,
            partials=0,
            coverage="85.00000",
            branches=0,
            methods=0,
            messages=0,
            sessions=1,
            complexity=0,
            complexity_total=0,
            diff=0,
        )

    def test_init(self, sample_rust_report):
        report = sample_rust_report
        assert report.totals.asdict() == {
            "files": 3,
            "lines": 20,
            "hits": 17,
            "misses": 3,
            "partials": 0,
            "coverage": "85.00000",
            "branches": 0,
            "methods": 0,
            "messages": 0,
            "sessions": 1,
            "complexity": 0,
            "complexity_total": 0,
            "diff": 0,
        }
        assert report.files == [
            "awesome/__init__.py",
            "tests/__init__.py",
            "tests/test_sample.py",
        ]
        assert sorted(f.name for f in report) == [
            "awesome/__init__.py",
            "tests/__init__.py",
            "tests/test_sample.py",
        ]

    def test_get(self, sample_rust_report):
        assert sample_rust_report.get("awesome/__init__.py").totals == ReportTotals(
            files=0,
            lines=10,
            hits=8,
            misses=2,
            partials=0,
            coverage="80.00000",
            branches=0,
            methods=0,
            messages=0,
            sessions=0,
            complexity=0,
            complexity_total=0,
            diff=0,
        )

    def test_size(self, sample_rust_report):
        assert sample_rust_report.size == 580

    def test_append(self, sample_rust_report):
        assert sample_rust_report.totals.asdict() == dict(
            files=3,
            lines=20,
            hits=17,
            misses=3,
            partials=0,
            coverage="85.00000",
            branches=0,
            methods=0,
            messages=0,
            sessions=1,
            complexity=0,
            complexity_total=0,
            diff=0,
        )
        some_file = ReportFile("somefile.cpp")
        some_file.append(
            1,
            ReportLine.create(
                coverage=1,
                sessions=[LineSession(0, 1), LineSession(1, 1), LineSession(2, 1)],
            ),
        )
        some_file.append(
            2,
            ReportLine.create(
                coverage=1, sessions=[LineSession(0, 0), LineSession(1, 1)]
            ),
        )
        some_file.append(
            3,
            ReportLine.create(
                coverage=1, sessions=[LineSession(0, 1), LineSession(1, 0)]
            ),
        )
        some_file.append(
            5,
            ReportLine.create(
                coverage=0, sessions=[LineSession(0, 0), LineSession(1, 0)]
            ),
        )
        sample_rust_report.append(some_file)
        assert sample_rust_report.totals.asdict() == dict(
            files=4,
            lines=24,
            hits=20,
            misses=4,
            partials=0,
            coverage="83.33333",
            branches=0,
            methods=0,
            messages=0,
            sessions=1,
            complexity=0,
            complexity_total=0,
            diff=0,
        )
        assert sample_rust_report.get("somefile.cpp").totals == ReportTotals(
            files=0,
            lines=4,
            hits=3,
            misses=1,
            partials=0,
            coverage="75.00000",
            branches=0,
            methods=0,
            messages=0,
            sessions=0,
            complexity=0,
            complexity_total=0,
            diff=0,
        )

    def test_differing_totals_calculation(self, mocker, sample_report):
        rust_analyzer = mocker.MagicMock(
            get_totals=mocker.MagicMock(return_value=ReportTotals(1, 999))
        )
        rust_report = mocker.MagicMock()
        r = ReadOnlyReport(rust_analyzer, rust_report, sample_report)
        assert r.totals == ReportTotals(1, 999)

    def test_differing_file_count_calculation(self, mocker, sample_report):
        rust_analyzer = mocker.MagicMock(
            get_totals=mocker.MagicMock(
                return_value=ReportTotals(
                    files=300,
                    lines=9,
                    hits=4,
                    misses=1,
                    partials=4,
                    coverage="44.44444",
                    branches=3,
                    methods=0,
                    messages=0,
                    sessions=4,
                    complexity=0,
                    complexity_total=0,
                    diff=0,
                )
            )
        )
        rust_report = mocker.MagicMock()
        r = ReadOnlyReport(rust_analyzer, rust_report, sample_report)
        assert r.totals == ReportTotals(
            files=300,
            lines=9,
            hits=4,
            misses=1,
            partials=4,
            coverage="44.44444",
            branches=3,
            methods=0,
            messages=0,
            sessions=4,
            complexity=0,
            complexity_total=0,
            diff=0,
        )

    def test_already_done_calculation(self, mocker, sample_rust_report):
        k = mocker.MagicMock()
        sample_rust_report._totals = k
        assert sample_rust_report.totals is k

    def test_inner_report_already_precalculated(self, mocker):
        inner_totals = mocker.MagicMock()
        rust_totals = mocker.MagicMock()
        rust_analyzer, rust_report = (
            mocker.MagicMock(get_totals=mocker.MagicMock(return_value=rust_totals)),
            mocker.MagicMock(),
        )
        inner_report = mocker.MagicMock(
            has_precalculated_totals=mocker.MagicMock(return_value=True),
            totals=inner_totals,
        )
        report = ReadOnlyReport(rust_analyzer, rust_report, inner_report)
        assert report.totals is inner_totals

    def test_inner_report_not_precalculated(self, mocker):
        inner_totals = mocker.MagicMock()
        rust_totals = mocker.MagicMock()
        rust_analyzer, rust_report = (
            mocker.MagicMock(get_totals=mocker.MagicMock(return_value=rust_totals)),
            mocker.MagicMock(),
        )
        inner_report = mocker.MagicMock(
            has_precalculated_totals=mocker.MagicMock(return_value=False),
            totals=inner_totals,
        )
        report = ReadOnlyReport(rust_analyzer, rust_report, inner_report)
        res = report.totals
        assert isinstance(res, ReportTotals)
        assert res.files is rust_totals.files
        assert res.lines is rust_totals.lines
        assert res.hits is rust_totals.hits
        assert res.misses is rust_totals.misses
        assert res.partials is rust_totals.partials
        assert res.coverage is rust_totals.coverage
        assert res.branches is rust_totals.branches
        assert res.methods is rust_totals.methods
        assert res.messages == 0
        assert res.sessions is rust_totals.sessions
        assert res.complexity is rust_totals.complexity
        assert res.complexity_total is rust_totals.complexity_total
        assert res.diff == 0

    def test_get_uploaded_flags_only_uploaded(self, sample_report):
        r = ReadOnlyReport.create_from_report(sample_report)
        assert r.get_uploaded_flags() == set(["complex", "simple"])

    def test_get_uploaded_flags(self, sample_report):
        sample_report.add_session(
            Session(flags=["banana", "apple"], session_type=SessionType.carriedforward)
        )
        sample_report.add_session(
            Session(flags=["sugar"], session_type=SessionType.carriedforward)
        )
        sample_report.add_session(
            Session(flags=["chocolate", "apple"], session_type=SessionType.uploaded)
        )
        r = ReadOnlyReport.create_from_report(sample_report)
        assert r.get_uploaded_flags() == set(
            ["complex", "simple", "apple", "chocolate"]
        )
        # second call to use the cached value
        assert r.get_uploaded_flags() == set(
            ["complex", "simple", "apple", "chocolate"]
        )
