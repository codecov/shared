from copy import deepcopy

from shared.reports.types.totals import SessionTotals, SessionTotalsArray


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
        "meta": {"real_length": 5},
        4: [0, 35, 35, 0, 0, "100", 5, 0, 0, 0, 0, 0, 0],
    }
    encoded_obj_string_index = {
        "meta": {"real_length": 5},
        "4": [0, 35, 35, 0, 0, "100", 5, 0, 0, 0, 0, 0, 0],
    }

    def test_decode_session_totals_array_from_legacy(self):
        expected = SessionTotalsArray(
            real_length=5,
            non_null_items={4: [0, 35, 35, 0, 0, "100", 5, 0, 0, 0, 0, 0, 0]},
        )
        result = SessionTotalsArray.build_from_encoded_data(self.legacy_encoded_obj)
        assert expected.real_length == result.real_length
        assert expected.non_null_items == result.non_null_items

    def test_decode_session_totals_array_from_legacy_all_nulls(self):
        expected = SessionTotalsArray(real_length=5)
        result = SessionTotalsArray.build_from_encoded_data(self.legacy_encoded_obj)
        assert expected.real_length == result.real_length
        assert expected.non_null_items == {}

    def test_decode_session_totals_array(self):
        encoded_obj_copy = deepcopy(self.encoded_obj)
        expected = SessionTotalsArray(
            real_length=5,
            non_null_items={4: [0, 35, 35, 0, 0, "100", 5, 0, 0, 0, 0, 0, 0]},
        )
        result = SessionTotalsArray.build_from_encoded_data(encoded_obj_copy)
        assert expected.real_length == result.real_length
        assert expected.non_null_items == result.non_null_items

    def test_decode_session_totals_array_string_indexes(self):
        encoded_obj_copy = deepcopy(self.encoded_obj_string_index)
        expected = SessionTotalsArray(
            real_length=5,
            non_null_items={4: [0, 35, 35, 0, 0, "100", 5, 0, 0, 0, 0, 0, 0]},
        )
        result = SessionTotalsArray.build_from_encoded_data(encoded_obj_copy)
        assert expected.real_length == result.real_length
        assert expected.non_null_items == result.non_null_items

    def test_decode_session_totals_array_no_meta(self):
        encoded_obj_copy = deepcopy(self.encoded_obj)
        encoded_obj_copy.pop("meta")
        expected = SessionTotalsArray(
            real_length=5,
            non_null_items={4: [0, 35, 35, 0, 0, "100", 5, 0, 0, 0, 0, 0, 0]},
        )
        result = SessionTotalsArray.build_from_encoded_data(encoded_obj_copy)
        assert expected.real_length == result.real_length
        assert expected.non_null_items == result.non_null_items

    def test_decode_session_totals_from_None(self):
        result = SessionTotalsArray.build_from_encoded_data(None)
        assert isinstance(result, SessionTotalsArray)
        assert result.real_length == 0
        assert result.non_null_items == {}

    def test_decode_session_totals_array_from_itself(self):
        obj = SessionTotalsArray(
            real_length=5,
            non_null_items={4: [0, 35, 35, 0, 0, "100", 5, 0, 0, 0, 0, 0, 0]},
        )
        result = SessionTotalsArray.build_from_encoded_data(obj)
        assert obj.real_length == result.real_length
        assert obj.non_null_items == result.non_null_items

    def test_encode(self):
        encoded_obj_copy = deepcopy(self.encoded_obj)
        obj = SessionTotalsArray(
            real_length=5,
            non_null_items={4: [0, 35, 35, 0, 0, "100", 5, 0, 0, 0, 0, 0, 0]},
        )
        encoded_obj = obj.to_database()
        assert encoded_obj == encoded_obj_copy

    def test_decode_then_encode(self):
        encoded_obj_copy = deepcopy(self.encoded_obj)
        obj = SessionTotalsArray.build_from_encoded_data(encoded_obj_copy)
        encoded_obj = obj.to_database()
        assert encoded_obj == self.encoded_obj

    def test_iteration(self):
        obj = SessionTotalsArray(
            real_length=5,
            non_null_items={
                4: [4, 35, 35, 0, 0, "100", 5, 0, 0, 0, 0, 0, 0],
                2: [2, 35, 35, 0, 0, "100", 5, 0, 0, 0, 0, 0, 0],
            },
        )
        expected_sessions_in_order = [
            [2, 35, 35, 0, 0, "100", 5, 0, 0, 0, 0, 0, 0],
            [4, 35, 35, 0, 0, "100", 5, 0, 0, 0, 0, 0, 0],
        ]
        for idx, session in enumerate(obj):
            assert session == expected_sessions_in_order[idx]

    def test_iteration_null(self):
        obj = SessionTotalsArray()
        for _ in obj:
            assert False

    def test_append(self):
        obj = SessionTotalsArray(
            real_length=5,
            non_null_items={4: [4, 35, 35, 0, 0, "100", 5, 0, 0, 0, 0, 0, 0]},
        )
        new_session = SessionTotals(1, 10, 8, 2, 0, "80")
        obj.append(new_session)
        assert obj.real_length == 6
        assert 5 in obj.non_null_items
        assert obj.non_null_items[5] == new_session

        obj.append(None)
        assert obj.real_length == 6
        assert 5 in obj.non_null_items
        assert obj.non_null_items[5] == new_session

    def test_equality(self):
        obj = SessionTotalsArray(
            real_length=5,
            non_null_items={4: [4, 35, 35, 0, 0, "100", 5, 0, 0, 0, 0, 0, 0]},
        )
        obj_equal = SessionTotalsArray(
            real_length=5,
            non_null_items={4: [4, 35, 35, 0, 0, "100", 5, 0, 0, 0, 0, 0, 0]},
        )
        obj_different_length = SessionTotalsArray(
            real_length=2,
            non_null_items={1: [4, 35, 35, 0, 0, "100", 5, 0, 0, 0, 0, 0, 0]},
        )
        obj_different_item = SessionTotalsArray(
            real_length=5,
            non_null_items={3: [4, 35, 35, 0, 0, "100", 5, 0, 0, 0, 0, 0, 0]},
        )

        assert obj == obj_equal
        assert obj != obj_different_length
        assert obj != obj_different_item

    def test_bool(self):
        obj_null = SessionTotalsArray()
        obj_valid = SessionTotalsArray(real_length=1)
        if obj_null:
            assert False
        if not obj_valid:
            assert False
