from src.utils.sessions import Session


def test_sessions():
    s = Session('id', 'totals', 'time', 'archive', 'flags', 'provider', 'build', 'job', 'url', 'state', 'env', 'name')
    assert s._encode() == {
            't': 'totals',
            'd': 'time',
            'a': 'archive',
            'f': 'flags',
            'c': 'provider',
            'n': 'build',
            'N': 'name',
            'j': 'job',
            'u': 'url',
            'p': 'state',
            'e': 'env',
        }
