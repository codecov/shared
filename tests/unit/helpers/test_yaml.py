import pytest
from covreports.helpers.yaml import walk


@pytest.mark.parametrize('_dict, keys, _else, res', [
    ({'a': 'b'}, ('a',), 'c', 'b'),
    ({'a': {'b': 'c'}}, ('a', 'b'), 'd', 'c'),
    ({'a': {'_': 'c'}}, ('a', 'b'), 'd', 'd'),
    ({'a': {'_': 'c'}}, ('a', 'b'), None,  None),
])
def test_yaml_walk(_dict, keys, _else, res):
    assert walk(_dict, keys, _else) == res
