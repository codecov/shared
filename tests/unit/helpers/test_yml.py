from src.helpers.yml import walk


def test_walk():
    assert walk({'a': 'b'}, ('a',), 'c') == 'b'
    assert walk({'a': {'b': 'c'}}, ('a', 'b'), 'd') == 'c'
    assert walk({'a': {'_': 'c'}}, ('a', 'b'), 'd') == 'd'
    assert walk({'a': {'_': 'c'}}, ('a', 'b'), None) is None
