from src.utils.Yaml import Yaml


def test_yaml_walk():
    assert Yaml.walk({'a': 'b'}, ('a',), 'c') == 'b'
    assert Yaml.walk({'a': {'b': 'c'}}, ('a', 'b'), 'd') == 'c'
    assert Yaml.walk({'a': {'_': 'c'}}, ('a', 'b'), 'd') == 'd'
    assert Yaml.walk({'a': {'_': 'c'}}, ('a', 'b'), None) is None
