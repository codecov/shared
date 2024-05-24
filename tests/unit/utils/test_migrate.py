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


@pytest.mark.unit
@pytest.mark.parametrize(
    "totals, res",
    [
        (
            [203, 4076, 2549, 1527, 0, "62.53680", 574, 0, 0, 0, 0, 0],
            {
                "branches": 574,
                "complexity": 0,
                "complexity_total": 0,
                "coverage": 62.5368,
                "diff": 0,
                "files": 203,
                "hits": 2549,
                "lines": 4076,
                "messages": 0,
                "methods": 0,
                "misses": 1527,
                "partials": 0,
                "sessions": 0,
            },
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
            {
                "branches": 574,
                "complexity": 0,
                "complexity_total": 0,
                "coverage": 62.5368,
                "diff": 0,
                "files": 203,
                "hits": 2549,
                "lines": 4076,
                "messages": 0,
                "methods": 0,
                "misses": 1527,
                "partials": 0,
                "sessions": 0,
            },
        ),
    ],
)
def test_totals_to_dict(totals, res):
    assert totals_to_dict(totals) == res
