from types import GeneratorType

import pytest

from shared.helpers.yaml import default_if_true, walk


def test_yaml_walk(mocker):
    assert walk({"a": "b"}, ("a",), "c") == "b"
    assert walk({"a": {"b": "c"}}, ("a", "b"), "d") == "c"
    assert walk({"a": mocker.Mock(b="banana")}, ("a", "b"), "d") == "banana"
    assert walk({"a": {"_": "c"}}, ("a", "b"), "d") == "d"
    assert walk({"a": {"_": "c"}}, ("a", "b"), None) is None


@pytest.mark.parametrize(
    "a, b",
    [
        (True, {"default": {}}),
        (None, {}),
        (False, {}),
        ({"a": False, "b": True}, {"b": {}}),
        ({"custom": {"enabled": False}}, {}),
        ({"custom": {"enabled": True}}, {"custom": {"enabled": True}}),
    ],
)
def test_default_if_true(a, b):
    res = default_if_true(a)
    if isinstance(res, GeneratorType):
        assert dict(res) == b
    else:
        assert res == b
