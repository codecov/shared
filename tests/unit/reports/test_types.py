from decimal import Decimal

from shared.reports.types import (
    Change,
    CoverageDatapoint,
    LineSession,
    NetworkFile,
    ReportLine,
    ReportTotals,
)


def test_changes_init():
    change = Change(
        path="modified.py",
        in_diff=True,
        totals=ReportTotals(
            files=0,
            lines=0,
            hits=-2,
            misses=1,
            partials=0,
            coverage=-23.333330000000004,
            branches=0,
            methods=0,
            messages=0,
            sessions=0,
            complexity=0,
            complexity_total=0,
            diff=0,
        ),
    )
    assert isinstance(change.totals, ReportTotals)
    assert change.totals == ReportTotals(
        files=0,
        lines=0,
        hits=-2,
        misses=1,
        partials=0,
        coverage=-23.333330000000004,
        branches=0,
        methods=0,
        messages=0,
        sessions=0,
        complexity=0,
        complexity_total=0,
        diff=0,
    )


def test_changes_init_no_internal_types():
    change = Change(
        path="modified.py",
        in_diff=True,
        totals=[0, 0, -2, 1, 0, -23.333330000000004, 0, 0, 0, 0, 0, 0, 0],
    )
    assert isinstance(change.totals, ReportTotals)
    assert change.totals == ReportTotals(
        files=0,
        lines=0,
        hits=-2,
        misses=1,
        partials=0,
        coverage=-23.333330000000004,
        branches=0,
        methods=0,
        messages=0,
        sessions=0,
        complexity=0,
        complexity_total=0,
        diff=0,
    )


def test_reportline_as_tuple():
    report_line = ReportLine.create(
        coverage=Decimal("10"),
        type="b",
        sessions=[LineSession(1, 0), LineSession(2, "1/2", 1)],
        complexity="10",
    )
    assert report_line.astuple() == (
        Decimal("10"),
        "b",
        [(1, 0), (2, "1/2", 1, None, None)],
        None,
        "10",
        None,
    )


def test_coverage_datapoint_as_tuple():
    cd = CoverageDatapoint(
        sessionid=3, coverage=1, coverage_type="b", label_ids=[1, 2, 3]
    )
    assert cd.astuple() == (3, 1, "b", [1, 2, 3])
    cd = CoverageDatapoint(
        sessionid=3, coverage=1, coverage_type="b", label_ids=["1", "2", "3"]
    )
    assert cd.astuple() == (3, 1, "b", [1, 2, 3])


class TestNetworkFile(object):
    def test_networkfile_as_tuple(self):
        network_file = NetworkFile(
            totals=ReportTotals(
                files=0,
                lines=0,
                hits=-2,
                misses=1,
                partials=0,
                coverage=-23.333330000000004,
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
        assert network_file.astuple() == (
            (0, 0, -2, 1, 0, -23.333330000000004, 0, 0, 0, 0, 0, 0, 0),
            None,
            None,
        )


class TestReportTotals(object):
    def test_encoded_report_total(self):
        obj = ReportTotals(*[0, 35, 35, 0, 0, "100", 5, 0, 0, 0, 0, 0, 0])
        obj_1 = ReportTotals(*[0, 35, 35, 0, 0, "100", 5])
        assert obj == obj_1
        assert obj.to_database() == obj_1.to_database()
