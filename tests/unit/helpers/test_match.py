import pytest
from src.utils.match import *


@pytest.mark.parametrize('patterns, string, boolean', [
    (['branch*'],'branch', True),
    (['features/.*', 'develop'], 'features/a', True),
    (['feature/.*', 'patch.*'], 'patch-1', True),
    (['feature'], 'feature', True),
    (['.*.*/.*.py'], 'folder/to/path.py', True),
    (None, 'master',True),
    (['master'], 'master', True),
    (['.*', '!patch'], 'patch',False),
    (['!patch'], 'patch',False),
    (['!patch'], 'master',True),
    (['^!patch'], 'master',True),
    (['.*', '!patch.*'], 'patch-a',False),
    (['!wip.*'], 'master',True),
    (['!wip.*', '.*coverage.*'], 'go-coverage',True),
    (['.*', '!patch.*'], 'patch-a',False),
    (['.*', '!patch'], 'master',True),
    (['!patch', 'master'], 'master' ,True),
    (['featur$'], 'feature',False),
])
def test_match(patterns, string, boolean):
    assert match(patterns, string) is boolean


@pytest.mark.parametrize('patterns, match_any_of_these, boolean', [
    (['.*'], ['a', Exception()], True),
    (['folder/.*'], ['folder/file', Exception()], True),
    (['a'], None, False),
    (['a'], [], False),
    (['folder'], ['file', 'folder'], True),
    (['folder'], ['file'], False),
    (['folder'], ['file', 'another'], False),
])
def test_match_any(patterns, match_any_of_these, boolean):
    assert match_any(patterns, match_any_of_these) is boolean
