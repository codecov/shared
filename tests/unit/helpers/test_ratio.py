import pytest

from shared.helpers.numeric import ratio


@pytest.mark.parametrize(
    "x, y, percent", [(2, 2, "100"), (0, 2, "0"), (2, 0, "0"), (1, 2, "50.00000")]
)
def test_ratio(x, y, percent):
    assert ratio(x, y) == percent
