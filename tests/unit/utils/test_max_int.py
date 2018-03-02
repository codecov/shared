import pytest
from src.utils.MaxInt import MaxInt


@pytest.mark.parametrize('string, number', [
    ('7', 7),
    ('1231412412', 99999),
])
def test_max_int(string, number):
    assert MaxInt(string).get_value() == number
