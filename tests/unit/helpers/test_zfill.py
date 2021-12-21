import pytest

from shared.helpers.zfill import zfill


@pytest.mark.parametrize(
    "lst, index, value, res",
    [
        ([1, 2, 3, 4, 5], 2, 10, [1, 2, 10, 4, 5]),
        ([1, 2, 3], 10, 5, [1, 2, 3, None, None, None, None, None, None, None, 5]),
    ],
)
def test_zfill(lst, index, value, res):
    assert zfill(lst, index, value) == res
