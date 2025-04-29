import pytest

from shared.utils.match import *


@pytest.mark.unit
@pytest.mark.parametrize(
    "patterns, string, boolean",
    [
        (["branch*"], "branch", True),
        (["features/.*", "develop"], "features/a", True),
        (["feature/.*", "patch.*"], "patch-1", True),
        (["feature"], "feature", True),
        ([".*.*/.*.py"], "folder/to/path.py", True),
        (None, "main", True),
        (["main"], "main", True),
        ([".*", "!patch"], "patch", False),
        (["!patch"], "patch", False),
        (["!patch"], "main", True),
        (["^!patch"], "main", True),
        ([".*", "!patch.*"], "patch-a", False),
        (["!wip.*"], "main", True),
        (["!wip.*", ".*coverage.*"], "go-coverage", True),
        ([".*", "!patch.*"], "patch-a", False),
        ([".*", "!patch"], "main", True),
        (["!patch", "main"], "main", True),
        (["featur$"], "feature", False),
        (["/folder/.*"], "/folder/file", True),
        (["/folder/.*"], "/file", False),
        (["/.*"], "/any/path", True),
        (["/.*", "!/exclude"], "/exclude", False),
        (["!/exclude"], "/exclude", False),
        (["!/exclude"], "/include", True),
        (["*.py"], "file.py", True),
        (["*.py"], "file.txt", False),
        (["folder/*.py"], "folder/file.py", True),
        (["folder/*.py"], "folder/file.txt", False),
        (["**/*.py"], "folder/subfolder/file.py", True),
        (["**/*.py"], "folder/subfolder/file.txt", False),
    ],
)
def test_match(patterns, string, boolean):
    assert match(patterns, string) is boolean


@pytest.mark.parametrize(
    "patterns, match_any_of_these, boolean",
    [
        ([".*"], ["a", Exception()], True),
        (["folder/.*"], ["folder/file", Exception()], True),
        (["a"], None, False),
        (["a"], [], False),
        (["folder"], ["file", "folder"], True),
        (["folder"], ["file"], False),
        (["folder"], ["file", "another"], False),
        (["/folder/.*"], ["/folder/file", Exception()], True),
        (["/folder"], ["/file", "/folder"], True),
        (["/folder"], ["/file"], False),
        (["/folder"], ["/file", "/another"], False),
        (["*.py"], ["file.py", Exception()], True),
        (["*.py"], ["file.txt", Exception()], False),
        (["folder/*.py"], ["folder/file.py", Exception()], True),
        (["folder/*.py"], ["folder/file.txt", Exception()], False),
        (["**/*.py"], ["folder/subfolder/file.py", Exception()], True),
        (["**/*.py"], ["folder/subfolder/file.txt", Exception()], False),
    ],
)
def test_match_any(patterns, match_any_of_these, boolean):
    assert match_any(patterns, match_any_of_these) is boolean
