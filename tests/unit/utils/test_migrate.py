import pytest

from shared.utils.migrate import *


@pytest.mark.unit
@pytest.mark.parametrize(
    "totals, res",
    [
        (
            {
                "files": 203,
                "hit": 2549,
                "methods": 0,
                "branches": 574,
                "lines": 4076,
                "partial": 0,
                "missed": 1527,
            },
            [203, 4076, 2549, 1527, 0, "62.53680", 574, 0, 0, 0, 0],
        ),
        (
            {
                "f": 203,
                "h": 2549,
                "b": 574,
                "n": 4076,
                "p": 0,
                "c": "62.53680",
                "m": 1527,
            },
            [203, 4076, 2549, 1527, 0, "62.53680", 574, 0, 0, 0, 0, 0, 0],
        ),
        (
            [203, 4076, 2549, 1527, 0, "62.53680", 574, 0, 0, 0, 0, 0],
            [203, 4076, 2549, 1527, 0, "62.53680", 574, 0, 0, 0, 0, 0],
        ),
        (None, []),
    ],
)
def test_migrate_totals(totals, res):
    assert migrate_totals(totals) == res
