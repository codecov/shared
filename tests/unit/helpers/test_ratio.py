from src.helpers.ratio import ratio


def test_ratio_one():
    assert ratio(2, 2) == '100'


def test_ratio_zero():
    assert ratio(0, 2) == '0'
    assert ratio(2, 0) == '0'


def test_ratio_fraction():
    assert ratio(1, 2) == '50.00000'
