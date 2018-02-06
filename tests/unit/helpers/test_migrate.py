from src.helpers.migrate import migrate_totals


def test_migrate_totals_v1():
    res = migrate_totals({'files': 203, 'hit': 2549, 'methods': 0, 'branches': 574, 'lines': 4076, 'partial': 0, 'missed': 1527})
    assert res == [203, 4076, 2549, 1527, 0, '62.53680', 574, 0, 0, 0, 0]


def test_migrate_totals_v2():
    res = migrate_totals({"f": 203, "h": 2549, "m": 0, "b": 574, "n": 4076, "p": 0, "c": "62.53680",  "m": 1527})
    assert res == [203, 4076, 2549, 1527, 0, '62.53680', 574, 0, 0, 0, 0, 0, 0]


def test_migrate_totals_v3():
    same = [203, 4076, 2549, 1527, 0, '62.53680', 574, 0, 0, 0, 0, 0]
    assert migrate_totals(same) == same
