from src.helpers.ratio import ratio


def test_ratio():
    r = ratio(2, 2)
    assert r == '100'
