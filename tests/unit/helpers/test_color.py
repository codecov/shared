import pytest

from shared.helpers.color import coverage_to_color


@pytest.mark.parametrize(
    "range_low, range_high, cov, hex_val",
    [
        (70, 100, 60.0, "#e05d44"),
        (70, 100, 70.0, "#e05d44"),
        (70, 100, 80.0, "#efa41b"),
        (70, 100, 90.0, "#a3b114"),
        (70, 100, 100.0, "#4c1"),
        (70, 100, 99.99999, "#48cc10"),
        (50, 90, 95.0, "#4c1"),
    ],
)
def test_coverage_to_color(range_low, range_high, cov, hex_val):
    assert coverage_to_color(range_low, range_high)(cov).hex == hex_val
