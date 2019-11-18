import pytest
from covreports.helpers.yaml import walk, default_if_true
from types import GeneratorType


@pytest.mark.parametrize('_dict, keys, _else, res', [
    ({'a': 'b'}, ('a',), 'c', 'b'),
    ({'a': {'b': 'c'}}, ('a', 'b'), 'd', 'c'),
    ({'a': {'_': 'c'}}, ('a', 'b'), 'd', 'd'),
    ({'a': {'_': 'c'}}, ('a', 'b'), None,  None),
])
def test_yaml_walk(_dict, keys, _else, res):
    assert walk(_dict, keys, _else) == res


@pytest.mark.parametrize('a, b', [
    (True, {'default': {}}),
    (None, {}),
    (False, {}),
    ({'custom': {'enabled': False}}, {}),
    ({'custom': {'enabled': True}}, {'custom': {'enabled': True}})
])
def test_default_if_true(a, b):
    res = default_if_true(a)
    if isinstance(res, GeneratorType):
        assert dict(res) == b
    else:
        assert res == b
