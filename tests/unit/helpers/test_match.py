from src.helpers.match import match, match_any


def test_match():
    assert match(['branch*'], 'branch') is True
    assert match(['features/.*', 'develop'], 'features/a') is True
    assert match(['feature/.*', 'patch.*'], 'patch-1') is True
    assert match(['feature'], 'feature') is True
    assert match(['.*.*/.*.py'], 'folder/to/path.py') is True
    assert match(None, 'master') is True
    assert match(['master'], 'master') is True
    assert match(['.*', '!patch'], 'patch') is False
    assert match(['!patch'], 'patch') is False
    assert match(['!patch'], 'master') is True
    assert match(['^!patch'], 'master') is True
    assert match(['.*', '!patch.*'], 'patch-a') is False
    assert match(['!wip.*'], 'master') is True
    assert match(['!wip.*', '.*coverage.*'], 'go-coverage') is True
    assert match(['.*', '!patch.*'], 'patch-a') is False
    assert match(['.*', '!patch'], 'master') is True
    assert match(['!patch', 'master'], 'master') is True
    assert match(['featur$'], 'feature') is False


def test_match_any():
    assert match_any(['.*'], ['a', Exception()]) is True
    assert match_any(['folder/.*'], ['folder/file', Exception()]) is True
    assert match_any(['a'], None) is False
    assert match_any(['a'], []) is False
    assert match_any(['folder'], ['file', 'folder']) is True
    assert match_any(['folder'], ['file']) is False
    assert match_any(['folder'], ['file', 'another']) is False
