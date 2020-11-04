import pytest
from json import loads
import dataclasses
import pprint

from shared.reports.resources import (
    Report,
    ReportFile,
    ReportLine,
    LineSession,
    Session,
    ReportTotals,
)
from shared.reports.types import NetworkFile
from shared.reports.filtered import FilteredReportFile


@pytest.fixture
def sample_report():
    report = Report()
    first_file = ReportFile("file_1.go")
    second_file = ReportFile("file_2.go")
    third_file = ReportFile("location/file_1.py")
    first_file.append(
        1,
        ReportLine(
            coverage=1,
            sessions=[LineSession(0, 1), LineSession(1, 1), LineSession(2, 1)],
        ),
    )
    first_file.append(
        2, ReportLine(coverage=1, sessions=[LineSession(0, 0), LineSession(1, 1)])
    )
    first_file.append(
        3, ReportLine(coverage=1, sessions=[LineSession(0, 1), LineSession(1, 0)])
    )
    first_file.append(
        5, ReportLine(coverage=0, sessions=[LineSession(0, 0), LineSession(1, 0)])
    )
    first_file.append(
        6,
        ReportLine(
            coverage="1/2",
            sessions=[LineSession(0, "1/2"), LineSession(1, 0), LineSession(2, "1/4")],
        ),
    )
    second_file.append(12, ReportLine(coverage=1, sessions=[[0, 1]]))
    second_file.append(51, ReportLine(coverage="1/2", type="b", sessions=[[0, "1/2"]]))
    third_file.append(100, ReportLine(coverage="1/2", type="b", sessions=[[3, "1/2"]]))
    third_file.append(
        101, ReportLine(coverage="1/2", type="b", sessions=[[2, "1/2"], [3, "1/2"]])
    )
    report.append(first_file)
    report.append(second_file)
    report.append(third_file)
    report.add_session(Session(id=0, flags=["simple"]))
    report.add_session(Session(id=1, flags=["complex"]))
    report.add_session(Session(id=2, flags=["complex", "simple"]))
    report.add_session(Session(id=3, flags=[]))
    # TODO manually fix Session totals because the defautl logic doesn't
    return report


class TestFilteredReportFile(object):
    def test_name(self):
        first_file = ReportFile("file_1.go")
        f = FilteredReportFile(first_file, [1])
        assert f.name == "file_1.go"

    def test_eof(self):
        first_file = ReportFile("file_1.go")
        f = FilteredReportFile(first_file, [1])
        assert f.eof == 1
        assert f.eof == first_file.eof

    def test_totals(self):
        first_file = ReportFile("file_1.go")
        first_file.append(
            1,
            ReportLine(
                coverage=1,
                sessions=[LineSession(0, 1), LineSession(1, 1), LineSession(2, 1)],
            ),
        )
        first_file.append(
            2, ReportLine(coverage=1, sessions=[LineSession(0, 0), LineSession(1, 1)])
        )
        first_file.append(
            3, ReportLine(coverage=1, sessions=[LineSession(0, 1), LineSession(1, 0)])
        )
        first_file.append(
            5, ReportLine(coverage=0, sessions=[LineSession(0, 0), LineSession(1, 0)])
        )
        first_file.append(
            6,
            ReportLine(
                coverage="1/2",
                sessions=[
                    LineSession(0, "1/2"),
                    LineSession(1, 0),
                    LineSession(2, "1/4"),
                ],
            ),
        )
        f = FilteredReportFile(first_file, [1])
        expected_result = ReportTotals(
            files=0,
            lines=5,
            hits=2,
            misses=3,
            partials=0,
            coverage="40.00000",
            branches=0,
            methods=0,
            messages=0,
            sessions=0,
            complexity=0,
            complexity_total=0,
            diff=0,
        )
        assert f.totals == expected_result
        # calling a second time to hit cache
        assert f.totals == expected_result
        assert f._totals == expected_result

    def test_calculate_totals_from_lines(self):
        line_1 = (1, ReportLine(coverage=1, sessions=[[0, 1]], complexity=[1, 3]))
        line_2 = (
            2,
            ReportLine(coverage=1, sessions=[[0, 1], [1, 1]], complexity=1),
        )
        line_3 = (3, ReportLine(coverage=0, sessions=[[0, 0]]))
        expected_result = ReportTotals(
            files=0,
            lines=3,
            hits=2,
            misses=1,
            partials=0,
            coverage="66.66667",
            branches=0,
            methods=0,
            messages=0,
            sessions=0,
            complexity=2,
            complexity_total=3,
            diff=0,
        )
        assert (
            FilteredReportFile.calculate_totals_from_lines([line_1, line_2, line_3])
            == expected_result
        )


class TestFilteredReport(object):
    def test_no_real_filter(self, sample_report):
        assert sample_report.filter(None, None) is sample_report

    def test_get(self, sample_report):
        assert sample_report.filter(paths=[".*.go"]).get("location/file_1.py") is None
        assert isinstance(
            sample_report.filter(paths=[".*.go"]).get("file_1.go"), ReportFile
        )
        assert isinstance(
            sample_report.filter(paths=[".*.go"], flags=["simple"]).get("file_1.go"),
            FilteredReportFile,
        )
        assert sample_report.get("location/file_1.py") is not None
        assert (
            sample_report.filter(paths=[".*.go"], flags=["simple"]).get("myfile.go")
            is None
        )

    def test_normal_totals(self, sample_report):
        assert sample_report.totals == ReportTotals(
            files=3,
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

    def test_totals_already_calculated(self, sample_report, mocker):
        v = mocker.MagicMock()
        filtered_report = sample_report.filter(paths=[".*.go"])
        filtered_report._totals = v
        assert filtered_report.totals is v

    def test_path_filtered_totals(self, sample_report):
        assert sample_report.filter(paths=[".*.go"]).totals == ReportTotals(
            files=2,
            lines=7,
            hits=4,
            misses=1,
            partials=2,
            coverage="57.14286",
            branches=1,
            methods=0,
            messages=0,
            sessions=4,
            complexity=0,
            complexity_total=0,
            diff=0,
        )
        assert sample_report.filter(paths=[".*file.*"]).totals == ReportTotals(
            files=3,
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
        assert sample_report.filter(
            paths=["location.*", "file_1.go"]
        ).totals == ReportTotals(
            files=2,
            lines=7,
            hits=3,
            misses=1,
            partials=3,
            coverage="42.85714",
            branches=2,
            methods=0,
            messages=0,
            sessions=4,
            complexity=0,
            complexity_total=0,
            diff=0,
        )

    def test_flag_filtered_totals(self, sample_report):
        assert sample_report.filter(flags=["simple"]).totals == ReportTotals(
            files=3,
            lines=8,
            hits=3,
            misses=2,
            partials=3,
            coverage="37.50000",
            branches=2,
            methods=0,
            messages=0,
            sessions=2,
            complexity=0,
            complexity_total=0,
            diff=0,
        )
        assert sample_report.filter(flags=["complex"]).totals == ReportTotals(
            files=3,
            lines=6,
            hits=2,
            misses=2,
            partials=2,
            coverage="33.33333",
            branches=1,
            methods=0,
            messages=0,
            sessions=2,
            complexity=0,
            complexity_total=0,
            diff=0,
        )
        assert sample_report.filter(flags=["simple", "complex"]).totals == ReportTotals(
            files=3,
            lines=8,
            hits=4,
            misses=1,
            partials=3,
            coverage="50.00000",
            branches=2,
            methods=0,
            messages=0,
            sessions=3,
            complexity=0,
            complexity_total=0,
            diff=0,
        )
        assert sample_report.filter(flags=[".*"]).totals == ReportTotals(
            files=3,
            lines=8,
            hits=4,
            misses=1,
            partials=3,
            coverage="50.00000",
            branches=2,
            methods=0,
            messages=0,
            sessions=3,
            complexity=0,
            complexity_total=0,
            diff=0,
        )

    def test_calculate_diff(self, sample_report):
        diff = {
            "files": {
                "file_1.go": {
                    "type": "modified",
                    "segments": [{"header": list("1313"), "lines": list("---+++")}],
                },
                "location/file_1.py": {
                    "type": "modified",
                    "segments": [
                        {"header": ["100", "3", "100", "3"], "lines": list("-+-+-+")}
                    ],
                },
                "deleted.py": {"type": "deleted",},
            }
        }
        res = sample_report.filter(paths=[".*go"]).calculate_diff(diff)
        expected_result = {
            "files": {
                "file_1.go": ReportTotals(
                    files=0, lines=3, hits=3, misses=0, partials=0, coverage="100"
                ),
            },
            "general": ReportTotals(
                files=1,
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
            ),
        }
        assert res["files"] == expected_result["files"]
        assert res["general"] == expected_result["general"]
        assert res == expected_result
        second_res = sample_report.filter(paths=["location.*"]).calculate_diff(diff)
        second_expected_result = {
            "files": {
                "location/file_1.py": ReportTotals(
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
            },
            "general": ReportTotals(
                files=1,
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
            ),
        }
        assert (
            sample_report.filter(paths=["location.*"]).apply_diff(diff)
            == second_expected_result["general"]
        )
        assert second_res["files"] == second_expected_result["files"]
        assert second_res["general"] == second_expected_result["general"]
        assert second_res == second_expected_result

    def test_calculate_diff_nothing_related_diff(self, sample_report):
        diff = {
            "files": {
                "random.go": {
                    "type": "modified",
                    "segments": [{"header": list("1313"), "lines": list("---+++")}],
                },
                "random.py": {
                    "type": "modified",
                    "segments": [
                        {"header": ["100", "3", "100", "3"], "lines": list("-+-+-+")}
                    ],
                },
            }
        }
        expected_result = {
            "files": {},
            "general": ReportTotals(
                files=0,
                lines=0,
                hits=0,
                misses=0,
                partials=0,
                coverage=None,
                branches=0,
                methods=0,
                messages=0,
                sessions=0,
                complexity=None,
                complexity_total=None,
                diff=0,
            ),
        }
        res = sample_report.filter(
            paths=["location.*"], flags=["simple"]
        ).calculate_diff(diff)
        assert res == expected_result

    def test_calculate_diff_empty_diff(self, sample_report):
        diff = {"files": {}}
        res = sample_report.filter(
            paths=["location.*"], flags=["simple"]
        ).calculate_diff(diff)
        assert res is None

    def test_calculate_diff_both_filters(self, sample_report):
        diff = {
            "files": {
                "file_1.go": {
                    "type": "modified",
                    "segments": [{"header": list("1313"), "lines": list("---+++")}],
                },
                "location/file_1.py": {
                    "type": "modified",
                    "segments": [
                        {"header": ["100", "3", "100", "3"], "lines": list("-+-+-+")}
                    ],
                },
            }
        }
        third_res = sample_report.filter(
            paths=["location.*"], flags=["simple"]
        ).calculate_diff(diff)
        third_expected_result = {
            "files": {
                "location/file_1.py": ReportTotals(
                    files=0,
                    lines=1,
                    hits=0,
                    misses=0,
                    partials=1,
                    coverage="0",
                    branches=1,
                    methods=0,
                    messages=0,
                    sessions=0,
                    complexity=0,
                    complexity_total=0,
                    diff=0,
                )
            },
            "general": ReportTotals(
                files=1,
                lines=1,
                hits=0,
                misses=0,
                partials=1,
                coverage="0",
                branches=1,
                methods=0,
                messages=0,
                sessions=0,
                complexity=0,
                complexity_total=0,
                diff=0,
            ),
        }
        assert (
            third_res["files"]["location/file_1.py"]
            == third_expected_result["files"]["location/file_1.py"]
        )
        assert third_res["files"] == third_expected_result["files"]
        assert third_res["general"] == third_expected_result["general"]
        assert third_res == third_expected_result
        assert (
            sample_report.filter(paths=["location.*"], flags=["simple"]).apply_diff(
                diff
            )
            == third_expected_result["general"]
        )
        assert diff == {
            "files": {
                "file_1.go": {
                    "type": "modified",
                    "segments": [
                        {
                            "header": ["1", "3", "1", "3"],
                            "lines": ["-", "-", "-", "+", "+", "+"],
                        }
                    ],
                },
                "location/file_1.py": {
                    "type": "modified",
                    "segments": [
                        {
                            "header": ["100", "3", "100", "3"],
                            "lines": ["-", "+", "-", "+", "-", "+"],
                        }
                    ],
                    "totals": ReportTotals(
                        files=0,
                        lines=1,
                        hits=0,
                        misses=0,
                        partials=1,
                        coverage="0",
                        branches=1,
                        methods=0,
                        messages=0,
                        sessions=0,
                        complexity=0,
                        complexity_total=0,
                        diff=0,
                    ),
                },
            },
            "totals": ReportTotals(
                files=1,
                lines=1,
                hits=0,
                misses=0,
                partials=1,
                coverage="0",
                branches=1,
                methods=0,
                messages=0,
                sessions=0,
                complexity=0,
                complexity_total=0,
                diff=0,
            ),
        }

    def test_apply_diff_none(self, sample_report):
        assert (
            sample_report.filter(paths=["location.*"], flags=["simple"]).apply_diff(
                None
            )
            is None
        )

    def test_apply_diff_not_saving(self, sample_report):
        diff = {
            "files": {
                "file_1.go": {
                    "type": "modified",
                    "segments": [{"header": list("1313"), "lines": list("---+++")}],
                },
                "location/file_1.py": {
                    "type": "modified",
                    "segments": [
                        {"header": ["100", "3", "100", "3"], "lines": list("-+-+-+")}
                    ],
                },
            }
        }
        res = sample_report.filter(paths=["location.*"], flags=["simple"]).apply_diff(
            diff, _save=False
        )
        third_expected_result = ReportTotals(
            files=1,
            lines=1,
            hits=0,
            misses=0,
            partials=1,
            coverage="0",
            branches=1,
            methods=0,
            messages=0,
            sessions=0,
            complexity=0,
            complexity_total=0,
            diff=0,
        )

        assert res == third_expected_result
        assert diff == {
            "files": {
                "file_1.go": {
                    "type": "modified",
                    "segments": [{"header": list("1313"), "lines": list("---+++")}],
                },
                "location/file_1.py": {
                    "type": "modified",
                    "segments": [
                        {"header": ["100", "3", "100", "3"], "lines": list("-+-+-+")}
                    ],
                },
            }
        }

    def test_network(self, sample_report):
        print(list(sample_report.filter(paths=[".*go"]).network))
        assert list(sample_report.filter(paths=[".*go"]).network) == [
            (
                "file_1.go",
                NetworkFile(
                    totals=ReportTotals(
                        files=0,
                        lines=5,
                        hits=3,
                        misses=1,
                        partials=1,
                        coverage="60.00000",
                        branches=0,
                        methods=0,
                        messages=0,
                        sessions=0,
                        complexity=0,
                        complexity_total=0,
                        diff=0,
                    ),
                    session_totals=None,
                    diff_totals=None,
                ),
            ),
            (
                "file_2.go",
                NetworkFile(
                    totals=ReportTotals(
                        files=0,
                        lines=2,
                        hits=1,
                        misses=0,
                        partials=1,
                        coverage="50.00000",
                        branches=1,
                        methods=0,
                        messages=0,
                        sessions=0,
                        complexity=0,
                        complexity_total=0,
                        diff=0,
                    ),
                    session_totals=None,
                    diff_totals=None,
                ),
            ),
        ]

    def test_iter_path_filter(self, sample_report):
        r = list(sample_report.filter(paths=[".*go"]))
        assert len(r) == 2
        r = sorted(r, key=lambda r: r.name)
        assert r[0].name == "file_1.go"
        assert r[0].totals == ReportTotals(
            files=0,
            lines=5,
            hits=3,
            misses=1,
            partials=1,
            coverage="60.00000",
            branches=0,
            methods=0,
            messages=0,
            sessions=0,
            complexity=0,
            complexity_total=0,
            diff=0,
        )
        assert r[1].name == "file_2.go"
        assert r[1].totals == ReportTotals(
            files=0,
            lines=2,
            hits=1,
            misses=0,
            partials=1,
            coverage="50.00000",
            branches=1,
            methods=0,
            messages=0,
            sessions=0,
            complexity=0,
            complexity_total=0,
            diff=0,
        )

    def test_iter_path_and_flag_filter(self, sample_report):
        r = list(sample_report.filter(paths=[".*go"], flags=["simple"]))
        assert len(r) == 2
        r = sorted(r, key=lambda r: r.name)
        assert r[0].name == "file_1.go"
        assert r[0].totals == ReportTotals(
            files=0,
            lines=5,
            hits=2,
            misses=2,
            partials=1,
            coverage="40.00000",
            branches=0,
            methods=0,
            messages=0,
            sessions=0,
            complexity=0,
            complexity_total=0,
            diff=0,
        )
        assert r[1].name == "file_2.go"
        assert r[1].totals == ReportTotals(
            files=0,
            lines=2,
            hits=1,
            misses=0,
            partials=1,
            coverage="50.00000",
            branches=1,
            methods=0,
            messages=0,
            sessions=0,
            complexity=0,
            complexity_total=0,
            diff=0,
        )
