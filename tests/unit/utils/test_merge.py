from fractions import Fraction

import pytest

from shared.utils.merge import (
    CoverageDatapoint,
    LineSession,
    LineType,
    ReportLine,
    branch_type,
    get_complexity_from_sessions,
    get_coverage_from_sessions,
    line_type,
    merge_all,
    merge_branch,
    merge_coverage,
    merge_datapoints,
    merge_line,
    merge_line_session,
    merge_missed_branches,
    merge_partial_line,
    partials_to_line,
)


@pytest.mark.unit
@pytest.mark.parametrize(
    "cov_list, res",
    [([0], 0), ([0, 1], 1), ([0, "0/2", "1/2"], "1/2"), ([1, "0/2", "1/2"], "2/2")],
)
def test_merge_all(cov_list, res):
    assert merge_all(cov_list) == res


@pytest.mark.unit
@pytest.mark.parametrize(
    "b1, b2, res",
    [
        ("1/2", "2/2", "2/2"),
        ("0/2", "2/2", "2/2"),
        ("0/2", 1, 1),
        ("0/2", -1, -1),
        (0, "2/2", "2/2"),
        (True, "2/2", "2/2"),
        (None, "2/2", "2/2"),
        ("1/2", "2/3", "2/3"),
        ("1/2", "1/6", "1/6"),
        ("0/2", "0/2", "0/2"),
        ("0/2", "0/2", "0/2"),
        ("0/2", [[1, 2, None]], [[1, 2, None]]),
        ([[1, 2, None]], "0/2", [[1, 2, None]]),
    ],
)
def test_merge_branch(b1, b2, res):
    assert res == merge_branch(b1, b2), "%s <> %s expected %s got %s" % (
        b1,
        b2,
        res,
        str(merge_branch(b1, b2)),
    )
    assert res == merge_branch(b2, b1), "%s <> %s expected %s got %s" % (
        b2,
        b1,
        res,
        str(merge_branch(b2, b1)),
    )


# This immitates what a report.labels_index looks like
# It's an map idx -> label, so we can go from CoverageDatapoint.label_id to the actual label
# typically via Report.lookup_label_by_id
def lookup_label(label_id: int) -> str:
    lookup_table = {1: "banana", 2: "apple", 3: "simpletest"}
    return lookup_table[label_id]


def test_merge_datapoints():
    c_1 = CoverageDatapoint(sessionid=1, coverage=1, coverage_type=None, label_ids=None)
    c_1_copy = CoverageDatapoint(
        sessionid=1, coverage=1, coverage_type=None, label_ids=None
    )
    c_2 = CoverageDatapoint(sessionid=1, coverage=1, coverage_type=None, label_ids=[1])
    c_2_copy = CoverageDatapoint(
        sessionid=1, coverage=1, coverage_type=None, label_ids=[1]
    )
    c_2_other_session = CoverageDatapoint(
        sessionid=2, coverage=1, coverage_type=None, label_ids=[1]
    )
    c_3 = CoverageDatapoint(sessionid=1, coverage=1, coverage_type=None, label_ids=[2])
    assert [c_1, c_2] == merge_datapoints(
        [c_1],
        [c_2],
    )
    assert [c_1, c_2] == merge_datapoints(
        [c_2],
        [c_1],
    )
    assert [c_1, c_2, c_3] == merge_datapoints([c_2, c_1], [c_3])
    assert [c_1, c_2] == merge_datapoints([c_2, c_1], None)
    assert [c_1, c_2] == merge_datapoints([c_2, c_1], [None])
    assert [c_1, c_2, c_2_other_session] == merge_datapoints(
        [c_1, c_2, c_2_other_session], [c_1_copy, c_2_copy, c_2_other_session]
    )


@pytest.mark.unit
@pytest.mark.parametrize(
    "p1, p2, res",
    [
        ([], [[1, 2, 3]], [[1, 2, 3]]),
        ([[1, None, 1]], [], [[1, None, 1]]),  # one
        (
            [[1, None, 1]],
            [[3, 5, 1]],
            [[1, None, 1]],
        ),  # [--++--] inner join 1+&1 3-5&1 => 1+&1
        (
            [[1, None, 1]],
            [[1, 2, 0]],
            [[1, None, 1]],
        ),  # [--++--] inner join 1+&1 1-2&0 => 1+&1
        (
            [[None, 10, 1]],
            [[None, 20, 1]],
            [[0, 20, 1]],
        ),  # [++--] inner join -10&1 -20&1 => -20&1
        (
            [[None, 10, 0]],
            [[None, 20, 0]],
            [[0, 20, 0]],
        ),  # [++--] inner join -10&1 10-20&0 => same
        (
            [[1, 5, 0], [6, 10, 1]],
            [[10, 15, 1], [18, 20, 0]],
            [[1, 5, 0], [6, 15, 1], [18, 20, 0]],
        ),  # side join
        ([[0, 5, 1]], [[10, 20, 0]], [[0, 5, 1], [10, 20, 0]]),  # [-- --] outer join
        ([[None, 10, 0]], [[5, 20, 1]], [[0, 4, 0], [5, 20, 1]]),  # [--/--] reduce left
        (
            [[None, 10, 1]],
            [[5, 20, 0]],
            [[0, 10, 1], [11, 20, 0]],
        ),  # [--/--] reduce right
    ],
)
def test_merge_partial_lines(p1, p2, res):
    assert res == merge_partial_line(p1, p2)
    assert res == merge_partial_line(p2, p1)


@pytest.mark.unit
@pytest.mark.parametrize(
    "l1, l2, brm, res",
    [
        (1, 5, None, 5),
        (1, 0, None, 1),
        (True, False, None, True),
        (False, True, None, True),
        (1, None, None, 1),
        ("0/3", "0/3", ["1:12", "1:3", "10:22", "10:12"], "0/3"),
        (99999, 10, None, 99999),
        (0, [[1, 1, 0]], None, 0),
        (0, [[1, 1, 1]], None, 1),
        ([[1, 1, 0]], 0, None, 0),
        ([[1, 1, 1]], 0, None, 1),
        (0, -1, None, -1),
        ("1/2", "2/2", None, "2/2"),
        ("0/2", "2/2", None, "2/2"),
        ("1/2", "1/2", None, "1/2"),
        ("1/2", "1/2", [], "2/2"),
        ("1/2", "1/2", None, "1/2"),
        ("1/2", "1/2", ["56"], "1/2"),
        ("1/4", "1/4", ["56"], "3/4"),
        ("1/4", 0, None, "1/4"),
        ("0/4", "0/4", None, "0/4"),
        ("1/4", 1, None, "4/4"),
        (0, 0, None, 0),
    ],
)
def test_merge_coverage(l1, l2, brm, res):
    assert merge_coverage(l1, l2, brm) == res
    assert merge_coverage(l2, l1, brm) == res


@pytest.mark.unit
@pytest.mark.parametrize(
    "sessions, res",
    [
        (
            [LineSession(1, 0, [1, 2, 3]), LineSession(1, 0, [2, 3])],
            [2, 3],
        ),  # 2,3 missing
        ([LineSession(1, 0, [1, 2]), LineSession(1, 0, [1, 2])], [1, 2]),  # 1,2 missing
        ([LineSession(1, 0, [1, 2]), LineSession(1, 0, [3, 4])], []),  # 1,2 & 3,4 = []
        (
            [LineSession(1, 0, [1, 2]), LineSession(1, 0, [])],
            [],
        ),  # no branches missing on right
        ([LineSession("1/3", 0, [1, 2]), LineSession(1, 1)], []),  # because its a hit
        (
            [LineSession(1, 0, [1, 2]), LineSession(0, 0)],
            [1, 2],
        ),  # missed = carry over branches
        ([LineSession(1, 0), LineSession(1, 1)], None),
        ([], None),
        ([LineSession(1, 0, [1, 2])], [1, 2]),
    ],
)
def test_merge_missed_branches(sessions, res):
    assert merge_missed_branches(sessions) == res
    sessions.reverse()
    assert merge_missed_branches(sessions) == res


@pytest.mark.unit
@pytest.mark.parametrize(
    "l1, l2, expected_res",
    [
        (None, (1,), (1,)),  # no line to merge
        # sessions
        (
            ("1/2", None, [[1, "1/2", ["1"]]]),
            ("1/2", None, [[1, "1/2", ["2"]]]),
            ("2/2", None, [LineSession(1, "2/2", [])]),
        ),
        # session, w/ single mb
        (
            ("1/2", None, [[1, "1/2", ["1"]]]),
            ("1/2", None, [[1, "1/2", ["1"]]]),
            ("1/2", None, [LineSession(1, "1/2", ["1"])]),
        ),
        # different sessions
        (
            ("1/2", None, [[1, "1/2", ["1"]]]),
            ("1/2", None, [[2, "1/2", ["2"]]]),
            ("2/2", None, [LineSession(1, "1/2", ["1"]), LineSession(2, "1/2", ["2"])]),
        ),
        # add coverage
        ((1, None, [[1, 1]]), (2, None, [[1, 2]]), (2, None, [LineSession(1, 2)])),
        # merge sessions
        (
            ("2/2", None, [[1, "2/2"]]),
            ("0/2", None, [[2, "0/2", [1, 2]]]),
            ("2/2", None, [LineSession(1, "2/2"), LineSession(2, "0/2", [1, 2])]),
        ),
        # types
        ((1, None, [[1, 1]]), (1, "b", [[1, 1]]), (1, "b", [LineSession(1, 1)])),
        (
            (1, None, [[1, 1]], None, None, [(1, 1, None, [1])]),
            (1, "b", [[1, 1]], None, None, [(1, 1, "b", [3])]),
            (
                1,
                "b",
                [LineSession(1, 1)],
                None,  # messages
                None,  # complexity
                [
                    CoverageDatapoint(
                        sessionid=1,
                        coverage=1,
                        coverage_type=None,
                        label_ids=[1],
                    ),
                    CoverageDatapoint(
                        sessionid=1,
                        coverage=1,
                        coverage_type="b",
                        label_ids=[3],
                    ),
                ],
            ),
        ),
    ],
)
def test_merge_line(l1, l2, expected_res):
    assert merge_line(
        ReportLine.create(*l1) if l1 else None, ReportLine.create(*l2) if l2 else None
    ) == ReportLine.create(*expected_res)
    res = merge_line(
        ReportLine.create(*l2) if l2 else None, ReportLine.create(*l1) if l1 else None
    )
    try:
        assert res == ReportLine.create(*expected_res)
    except Exception:
        res.sessions.reverse()
        assert res == ReportLine.create(*expected_res)


@pytest.mark.xfail(reason='merging "incompatible" branches is broken right now')
def test_merge_with_incompatible_branches():
    s1 = LineSession(id=0, coverage="0/2", branches=["0:5", "0:6"])
    s2 = LineSession(id=0, coverage="0/1", branches=["0"])

    # If we would ignore the "missing branches", we would generate at least some kind of reasonable output.
    assert merge_branch("0/2", "0/1") == "0/2"

    # We expect this to be a miss, as both sessions are misses.
    # But the logic to merge coverages taking into account "missed branches" is broken.
    # Both coverages have a different number (and format) of missed branches.
    # Thus the intersection of missed branches is empty, and `merge_coverage` will
    # then just assume the line was hit, and generate a hit coverage accordingly.
    merged = merge_line_session(s1, s2)
    assert line_type(merged.coverage) == LineType.miss

    # Depending on the order of arguments, we end up with either `2/2` or `1/1`.
    # But given they are different formats (and number of branches), it is unclear
    # what to output from this as well.


@pytest.mark.unit
@pytest.mark.parametrize(
    "s1, s2, res",
    [
        (
            LineSession(0, "1/2", ["exit"]),
            LineSession(0, "2/2"),
            LineSession(0, "2/2", []),
        ),
        (LineSession(0, "1/2"), LineSession(0, "2/2"), LineSession(0, "2/2")),
        (
            LineSession(0, "1/2", ["exit"]),
            LineSession(0, "1/2", ["1"]),
            LineSession(0, "2/2", []),
        ),
        (
            LineSession(0, "2/3", ["1"]),
            LineSession(0, "1/3", ["1", "2"]),
            LineSession(0, "2/3", ["1"]),
        ),
        # (LineSession(0, '1/2'), LineSession(0, '2/2', ['branch']), LineSession(0, '1/2', ['branch'])),
        # (LineSession(0, 1, None, [1]), LineSession(0, 1), LineSession(0, 1, None, [1])),
        # (LineSession(0, 1, None, [2, 3]), LineSession(0, 1, None, [1, 5]), LineSession()),
    ],
)
def test_merge_line_session(s1, s2, res):
    assert merge_line_session(s1, s2) == res
    assert merge_line_session(s2, s1) == res


@pytest.mark.unit
@pytest.mark.parametrize(
    "line, _line_type",
    [
        (True, 2),
        (1, 0),
        (0, 1),
        (None, None),
        (False, None),
        (-1, -1),
        ("0/2", 1),
        (str("1/2"), 2),
        ("2/2", 0),
        (Fraction(1, 1), LineType.hit),
        (Fraction(2, 2), LineType.hit),
        (Fraction(1, 2), LineType.partial),
        (Fraction(0, 2), LineType.miss),
    ],
)
def test_line_type(line, _line_type):
    assert line_type(line) == _line_type


@pytest.mark.unit
@pytest.mark.parametrize(
    "x, y", [("0/2", 1), ("1/2", 2), ("2/2", 0), ("0", 1), ("1", 0)]
)
def test_branch_type(x, y):
    assert branch_type(x) == y
    assert branch_type(str(x)) == y


@pytest.mark.unit
@pytest.mark.parametrize(
    "partials, res",
    [
        ([(1, 5, 1), (5, 7, 0), (8, 9, 0)], "1/3"),
        ([(1, None, 1)], 1),
        ([(0, None, 1)], 1),
        ([(15, 18, 1)], 1),
        ([(1, None, 0)], 0),
        ([(0, None, 0)], 0),
        ([(0, 1, 0), (2, 3, 0)], "0/2"),
        ([(0, 1, 1), (3, 4, 1)], "2/2"),
    ],
)
def test_partials_to_line(partials, res):
    assert res == partials_to_line(partials)


@pytest.mark.unit
@pytest.mark.parametrize(
    "sessions, complexity",
    [([[1, 2, 3, 4, 5]], 5), ([[[1, 2], [2, 3], [3, 4], [4, 5], [5, 6]]], (5, 6))],
)
def test_get_complexity_from_sessions(sessions, complexity):
    sessions = [LineSession(*sess) for sess in sessions]
    assert get_complexity_from_sessions(sessions) == complexity
    assert get_complexity_from_sessions(sessions) == complexity


@pytest.mark.unit
def test_get_coverage_from_sessions():
    assert (
        get_coverage_from_sessions(
            [LineSession(1, "2/2"), LineSession(2, "0/2", [1, 2])]
        )
        == "2/2"
    )
