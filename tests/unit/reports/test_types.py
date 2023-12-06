from copy import deepcopy
from dataclasses import astuple
from decimal import Decimal

from shared.reports.types import (
    Change,
    CoverageDatapoint,
    LineSession,
    NetworkFile,
    ReportLine,
    ReportTotals,
    SessionTotals,
    SessionTotalsArray,
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
            session_totals=[
                None,
                None,
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
            {
                "meta": {"session_count": 4},
                2: [0, 0, -2, 1, 0, -23.333330000000004],
                3: [10, 0, -2, 1, 5, 89.33333, 0, 2],
            },
            None,
        )


class TestReportTotals(object):
    def test_encoded_report_total(self):
        obj = ReportTotals(*[0, 35, 35, 0, 0, "100", 5, 0, 0, 0, 0, 0, 0])
        obj_1 = ReportTotals(*[0, 35, 35, 0, 0, "100", 5])
        assert obj == obj_1
        assert obj.to_database() == obj_1.to_database()


class TestSessionTotalsArray(object):
    legacy_encoded_obj = [
        None,
        None,
        None,
        None,
        [0, 35, 35, 0, 0, "100", 5, 0, 0, 0, 0, 0, 0],
    ]
    legacy_encoded_obj_all_nulls = [None, None, None, None, None]
    encoded_obj = {
        "meta": {"session_count": 5},
        4: [0, 35, 35, 0, 0, "100", 5],
    }
    encoded_obj_string_index = {
        "meta": {"session_count": 5},
        "4": [0, 35, 35, 0, 0, "100", 5, 0, 0, 0, 0, 0, 0],
    }
    encoded_obj_string_no_meta = {
        "4": [0, 35, 35, 0, 0, "100", 5, 0, 0, 0, 0, 0, 0],
    }

    def test_decode_session_totals_array_from_legacy(self):
        expected = SessionTotalsArray(
            session_count=5,
            non_null_items={4: [0, 35, 35, 0, 0, "100", 5, 0, 0, 0, 0, 0, 0]},
        )
        result = SessionTotalsArray.build_from_encoded_data(self.legacy_encoded_obj)
        assert expected.session_count == result.session_count
        assert expected.non_null_items == result.non_null_items

    def test_decode_session_totals_array_from_legacy_all_nulls(self):
        expected = SessionTotalsArray(session_count=5)
        result = SessionTotalsArray.build_from_encoded_data(self.legacy_encoded_obj)
        assert expected.session_count == result.session_count
        assert expected.non_null_items == {}

    def test_decode_session_totals_array(self):
        encoded_obj_copy = deepcopy(self.encoded_obj)
        expected = SessionTotalsArray(
            session_count=5,
            non_null_items={4: [0, 35, 35, 0, 0, "100", 5, 0, 0, 0, 0, 0, 0]},
        )
        result = SessionTotalsArray.build_from_encoded_data(encoded_obj_copy)
        assert expected.session_count == result.session_count
        assert expected.non_null_items == result.non_null_items

    def test_decode_session_totals_array_string_indexes(self):
        encoded_obj_copy = deepcopy(self.encoded_obj_string_index)
        expected = SessionTotalsArray(
            session_count=5,
            non_null_items={4: [0, 35, 35, 0, 0, "100", 5, 0, 0, 0, 0, 0, 0]},
        )
        result = SessionTotalsArray.build_from_encoded_data(encoded_obj_copy)
        assert expected.session_count == result.session_count
        assert expected.non_null_items == result.non_null_items

    def test_decode_session_totals_array_string_indexes_no_meta(self):
        encoded_obj_copy = deepcopy(self.encoded_obj_string_no_meta)
        expected = SessionTotalsArray(
            session_count=5,
            non_null_items={4: [0, 35, 35, 0, 0, "100", 5, 0, 0, 0, 0, 0, 0]},
        )
        result = SessionTotalsArray.build_from_encoded_data(encoded_obj_copy)
        assert expected.session_count == result.session_count
        assert expected.non_null_items == result.non_null_items

    def test_decode_session_totals_array_no_meta(self):
        encoded_obj_copy = deepcopy(self.encoded_obj)
        encoded_obj_copy.pop("meta")
        expected = SessionTotalsArray(
            session_count=5,
            non_null_items={4: [0, 35, 35, 0, 0, "100", 5, 0, 0, 0, 0, 0, 0]},
        )
        result = SessionTotalsArray.build_from_encoded_data(encoded_obj_copy)
        assert expected.session_count == result.session_count
        assert expected.non_null_items == result.non_null_items

    def test_decode_session_totals_from_None(self):
        result = SessionTotalsArray.build_from_encoded_data(None)
        assert isinstance(result, SessionTotalsArray)
        assert result.session_count == 0
        assert result.non_null_items == {}

    def test_decode_session_totals_from_random_data(self):
        result = SessionTotalsArray.build_from_encoded_data("some random data")
        assert result is None

    def test_decode_session_totals_array_from_itself(self):
        obj = SessionTotalsArray(
            session_count=5,
            non_null_items={4: [0, 35, 35, 0, 0, "100", 5, 0, 0, 0, 0, 0, 0]},
        )
        result = SessionTotalsArray.build_from_encoded_data(obj)
        assert obj.session_count == result.session_count
        assert obj.non_null_items == result.non_null_items

    def test_encode(self):
        expected_result = {
            "meta": {"session_count": 5},
            4: [0, 35, 35, 0, 0, "100", 5],
        }
        obj = SessionTotalsArray(
            session_count=5,
            non_null_items={4: [0, 35, 35, 0, 0, "100", 5, 0, 0, 0, 0, 0, 0]},
        )
        encoded_obj = obj.to_database()
        assert encoded_obj == expected_result

    def test_encode_legacy_format(self, mock_configuration):
        mock_configuration.set_params({"setup": {"legacy_report_style": True}})
        expected_result = [None, None, None, None, [0, 35, 35, 0, 0, "100", 5]]
        obj = SessionTotalsArray(
            session_count=5,
            non_null_items={4: [0, 35, 35, 0, 0, "100", 5, 0, 0, 0, 0, 0, 0]},
        )
        encoded_obj = obj.to_database()
        assert encoded_obj == expected_result

    def test_decode_then_encode(self):
        encoded_obj_copy = deepcopy(self.encoded_obj)
        obj = SessionTotalsArray.build_from_encoded_data(encoded_obj_copy)
        encoded_obj = obj.to_database()
        assert encoded_obj == self.encoded_obj

    def test_iteration(self):
        obj = SessionTotalsArray(
            session_count=5,
            non_null_items={
                4: [4, 35, 35, 0, 0, "100", 5, 0, 0, 0, 0, 0, 0],
                2: [2, 35, 35, 0, 0, "100", 5, 0, 0, 0, 0, 0, 0],
            },
        )
        expected_sessions_in_order = [
            None,
            None,
            ReportTotals(*[2, 35, 35, 0, 0, "100", 5, 0, 0, 0, 0, 0, 0]),
            None,
            ReportTotals(*[4, 35, 35, 0, 0, "100", 5, 0, 0, 0, 0, 0, 0]),
            None,
        ]
        for idx, session in enumerate(obj):
            assert session == expected_sessions_in_order[idx]

    def test_expanding_legacy_format_all_nulls(self):
        session_totals = SessionTotalsArray.build_from_encoded_data(
            self.legacy_encoded_obj_all_nulls
        )
        assert list(session_totals) == self.legacy_encoded_obj_all_nulls

    def test_iteration_null(self):
        obj = SessionTotalsArray()
        for _ in obj:
            assert False

    def test_append(self):
        obj = SessionTotalsArray(
            session_count=5,
            non_null_items={4: [4, 35, 35, 0, 0, "100", 5, 0, 0, 0, 0, 0, 0]},
        )
        new_session = SessionTotals(1, 10, 8, 2, 0, "80")
        obj.append(new_session)
        assert obj.session_count == 6
        assert 5 in obj.non_null_items
        assert obj.non_null_items[5] == new_session

        obj.append(None)
        assert obj.session_count == 6
        assert 5 in obj.non_null_items
        assert obj.non_null_items[5] == new_session

    def test_equality(self):
        obj = SessionTotalsArray(
            session_count=5,
            non_null_items={4: [4, 35, 35, 0, 0, "100", 5, 0, 0, 0, 0, 0, 0]},
        )
        obj_equal = SessionTotalsArray(
            session_count=5,
            non_null_items={4: [4, 35, 35, 0, 0, "100", 5, 0, 0, 0, 0, 0, 0]},
        )
        obj_different_length = SessionTotalsArray(
            session_count=2,
            non_null_items={1: [4, 35, 35, 0, 0, "100", 5, 0, 0, 0, 0, 0, 0]},
        )
        obj_different_item = SessionTotalsArray(
            session_count=5,
            non_null_items={3: [4, 35, 35, 0, 0, "100", 5, 0, 0, 0, 0, 0, 0]},
        )

        assert obj == obj_equal
        assert obj != obj_different_length
        assert obj != obj_different_item
        assert obj != "something else"

    def test_repr(self):
        obj = SessionTotalsArray(
            session_count=5,
            non_null_items={4: [4, 35, 35, 0, 0, "100", 5, 0, 0, 0, 0, 0, 0]},
        )
        assert (
            str(SessionTotalsArray())
            == "SessionTotalsArray<session_count=0, non_null_items={}>"
        )
        assert (
            str(obj)
            == "SessionTotalsArray<session_count=5, non_null_items={4: ReportTotals(files=4, lines=35, hits=35, misses=0, partials=0, coverage='100', branches=5, methods=0, messages=0, sessions=0, complexity=0, complexity_total=0, diff=0)}>"
        )

    def test_bool(self):
        obj_null = SessionTotalsArray()
        obj_valid = SessionTotalsArray(session_count=1)
        if obj_null:
            assert False
        if not obj_valid:
            assert False

    def test_delete(self):
        obj = SessionTotalsArray(
            session_count=5,
            non_null_items={4: [4, 35, 35, 0, 0, "100", 5, 0, 0, 0, 0, 0, 0]},
        )
        assert obj.non_null_items == {4: ReportTotals(4, 35, 35, 0, 0, "100", 5)}
        assert obj.session_count == 5
        obj.delete(1)  # does nothing
        assert obj.non_null_items == {4: ReportTotals(4, 35, 35, 0, 0, "100", 5)}
        assert obj.session_count == 5
        obj.delete("4")  # deletes session 4 despite being str not int
        assert obj.non_null_items == {}
        assert obj.session_count == 5

    def test_delete_many(self):
        obj = SessionTotalsArray(
            session_count=5,
            non_null_items={
                4: [4, 35, 35, 0, 0, "100", 5, 0, 0, 0, 0, 0, 0],
                3: [4, 35, 35, 0, 0, "100", 5, 0, 0, 0, 0, 0, 0],
            },
        )
        assert obj.non_null_items == {
            4: ReportTotals(4, 35, 35, 0, 0, "100", 5),
            3: ReportTotals(4, 35, 35, 0, 0, "100", 5),
        }
        assert obj.session_count == 5
        obj.delete_many([3, 4])
        assert obj.non_null_items == {}
        assert obj.session_count == 5
