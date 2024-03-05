from unittest.mock import Mock, call

import shared.django_apps.executor
from shared.django_apps.executor import get_executor, run_in_executor


def test_get_executor():
    shared.django_apps.executor._executor = None
    new_executor = get_executor()
    assert new_executor != None
    assert new_executor == shared.django_apps.executor._executor


def test_run_in_executor(mocker):
    mock_executor = Mock()
    mocker.patch("shared.django_apps.executor.get_executor", return_value=mock_executor)

    def original_foo(arg1, arg2):
        return arg1 + arg2

    foo = run_in_executor(original_foo)

    foo("hello", "world")

    assert mock_executor.submit.call_args_list == [
        call(original_foo, "hello", "world"),
    ]
