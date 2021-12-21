from dataclasses import astuple
from decimal import Decimal

from shared.reports.types import (
    Change,
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
        messages=None,
        complexity="10",
    )
    assert report_line.astuple() == (
        Decimal("10"),
        "b",
        [(1, 0), (2, "1/2", 1, None, None)],
        None,
        "10",
    )


def test_networkfile_as_tuple():
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
        session_totals=[
            ReportTotals(
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
            ReportTotals(
                files=10,
                lines=0,
                hits=-2,
                misses=1,
                partials=5,
                coverage=89.333330000000004,
                branches=0,
                methods=2,
                messages=0,
                sessions=0,
                complexity=0,
                complexity_total=0,
                diff=0,
            ),
        ],
        diff_totals=None,
    )
    print(network_file.astuple())
    assert network_file.astuple() == (
        (0, 0, -2, 1, 0, -23.333330000000004, 0, 0, 0, 0, 0, 0, 0),
        [
            (0, 0, -2, 1, 0, -23.333330000000004, 0, 0, 0, 0, 0, 0, 0),
            (10, 0, -2, 1, 5, 89.33333, 0, 2, 0, 0, 0, 0, 0),
        ],
        None,
    )

    assert network_file.astuple() == astuple(network_file)
