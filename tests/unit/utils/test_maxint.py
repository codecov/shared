from src.utils.MaxInt import MaxInt


def test_maxint():
    maxint = MaxInt('7')
    assert maxint.get_value() == 7


def test_maxint_max():
    maxint = MaxInt('1231412412')
    assert maxint.get_value() == 99999
