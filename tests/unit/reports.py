import pytest
from src.reports import *


@pytest.mark.parametrize('_in, out', [
    ([(1, 2, 0), (4, 10, 1)], [[1, 2, 0], [4, 10, 1]]),  # outer == same
    ([[1, None, 1]], [[1, None, 1]]),  # single == same
    ([(2, 24, 1), (24, None, 0)], [[2, 24, 1], [24, None, 0]]),
    ([(2, 2, 1), (2, 2, 0)], None),
    ([(0, None, 28), (0, None, 0)], [[0, None, 28]]),
    ([(2, 35, 1), (35, None, 1)], [[2, None, 1]]),
    ([(2, 35, '1/2'), (35, None, '1/2')], [[2, None, '1/2']]),
    ([(2, 35, '1/2'), (35, None, '2/2')], [[2, 35, '1/2'], [35, None, '2/2']]),
    ([(None, 2, 1), (1, 5, 1)], [[0, 5, 1]]),
    ([(None, 1, 1), (1, 2, 0), (2, 3, 1)], [[1, 2, 0], [2, 3, 1]]),
    ([(1, None, 1), (2, None, 0)], [[1, None, 1]]),  # hit&miss overlay == hit
    ([(1, 5, 0), (4, 10, 1)], [[1, 4, 0], [4, 10, 1]]),  # intersect
    ([(1, 10, 0), (4, 6, 1)], [[1, 4, 0], [4, 6, 1], [6, 10, 0]]),  # inner overlay
])
def test_combine_partials(_in, out):
    assert combine_partials(_in) == out


@pytest.mark.parametrize('cov_list, res', [
    ([0], 0),
    ([0, 1], 1),
    ([0, '0/2', '1/2'], '1/2'),
    ([1, '0/2', '1/2'], '2/2'),
])
def test_merge_all(cov_list, res):
    assert merge_all(cov_list) == res


@pytest.mark.parametrize('x, y', [
    ('0/2', 1), ('1/2', 2), ('2/2', 0),
])
def test_branch_type(x, y):
    assert branch_type(x) == y
    assert branch_type(unicode(x)) == y

