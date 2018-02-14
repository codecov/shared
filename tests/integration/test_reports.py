import pytest
from src.reports import *
from tests.test_helpers import v2_to_v3


@pytest.mark.parametrize('diff, future, future_diff, res', [
    ({}, None, None, False),  # empty
    (None, None, None, False),  # empty
    ({'files': {}}, None, None, False),  # empty
    ({'files': {'b': {'type': 'new'}}}, None, None, False),  # new file not tracked
    ({'files': {'b': {'type': 'new'}}}, {'files': {'b': {'l': {'1': {'c': 1}}}}}, None, True),  # new file is tracked
    ({'files': {'b': {'type': 'modified'}}}, None, None, False),  # file not tracked in base or head
    ({'files': {'a': {'type': 'deleted'}}}, None, None, True),  # tracked file deleted
    ({'files': {'b': {'type': 'deleted'}}}, None, None, False),  # not-tracked file deleted
    ({'files': {'z': {'type': 'modified'}}}, None, None, True),  # modified file missing in base
    ({'files': {'a': {'type': 'modified'}}}, None, None, True),  # modified file missing in head
    ({'files': {'a': {'type': 'modified', 'segments': [{'header': [0, 1, 1, 2], 'lines': ['- a', '+ a']}]}}},
     {'files': {'a': {'l': {'1': {'c': 1}}}}}, None, True),  # tracked line deleted
    ({'files': {'a': {'type': 'modified', 'segments': [{'header': [0, 1, 1, 2], 'lines': ['- a', '+ a']}]}}},
     {'files': {'a': {'l': {'1': {'c': 1}}}}},
     {'files': {'a': {'type': 'modified'}}},
     True),  # tracked line deleted
    ({'files': {'a': {'type': 'modified', 'segments': [{'header': [10, 1, 10, 2], 'lines': ['- a', '+ a']}]}}},
     {'files': {'a': {'l': {'1': {'c': 1}}}}}, None, False)  # lines not tracked`
])
def test_does_diff_adjust_tracked_lines(diff, future, future_diff, res):
    report = v2_to_v3({'files': {'a': {'l': {'1': {'c': 1}, '2': {'c': 1}}}}})
    if future:
        future = v2_to_v3(future)
    else:
        future = v2_to_v3({'files': {'z': {}}})

    assert report.does_diff_adjust_tracked_lines(diff, future, future_diff) == res


def test_get_paths_from_flags():
    assert get_paths_from_flags(None, None) == []
    assert get_paths_from_flags({'yaml': {'flags': {'a': {'paths': ['b']}}}}, ['a']) == ['b']
    assert get_paths_from_flags({'yaml': {'flags': {'a': {'paths': ['b']}}}}, ['c']) == []


@pytest.mark.parametrize('totals, res', [
    ([ReportTotals(), ReportTotals(3, 3, 3, 3), ReportTotals()], ReportTotals(3, 3, 3, 3, 0, '100')),
    ([ReportTotals()], ReportTotals(1, 0, 0, 0, 0, '100')),
    ([], ReportTotals())
])
def test_sum_totals(totals, res):
    assert sum_totals(totals) == res


@pytest.mark.parametrize('totals, res', [
    ([None, xrange(6), xrange(6)], [2, 2, 4, 6, 8, '200.00000']),
    ([None, ReportTotals(*range(6)), ReportTotals(*range(6))], [2, 2, 4, 6, 8, '200.00000', 0, 0, 0, 0, 0, 0, 0]),
    ([], list((0,) * 13))
])
def test_agg_totals(totals, res):
    assert agg_totals(totals) == res


def test_reportfile_process_totals():
    report = v2_to_v3({'files': {'file': {'l': {'1': {'c': '1/2', 't': 'b'},
                                                         '2': {'c': 0},
                                                         '3': {'c': '1/2', 't': 'b'},
                                                         '4': {'c': 1},
                                                         '5': {'c': '2/2', 't': 'm'},
                                                         '6': {'c': 1},
                                                         '10': {'c': '4/4', 't': 'b'},
                                                         '11': {'c': 1}}}}})
    assert report.totals == ReportTotals(1, 8, 5, 1, 2, '62.50000', 3, 1, 0, 0)
    assert report['file'].totals == ReportTotals(0, 8, 5, 1, 2, '62.50000', 3, 1, 0, 0)
