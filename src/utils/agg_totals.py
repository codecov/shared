from src.utils.tuples import ReportTotals
from src.helpers.ratio import ratio
from itertools import izip, imap


def agg_totals(totals):
    totals = filter(None, totals)
    n_files = len(totals)
    totals = list(imap(_sum, izip(*totals)))
    if not totals:
        return list(ReportTotals.__new__.__defaults__)
    totals[0] = n_files
    totals[5] = ratio(totals[2], totals[1])
    return totals


def _sum(array):
    if array:
        if not isinstance(array[0], (type(None), basestring)):
            try:
                return sum(array)
            except:
                # https://sentry.io/codecov/v4/issues/159966549/
                return sum(map(lambda a: a if type(a) is int else 0, array))
    return None
