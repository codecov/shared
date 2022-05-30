import pytest

from shared.helpers.numeric import maxint


@pytest.mark.parametrize("string, number", [("7", 7), ("1231412412", 99999)])
def test_max_int(string, number):
    assert maxint(string) == number
