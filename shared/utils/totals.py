from shared.reports.types import ReportTotals
from shared.helpers.numeric import ratio

from operator import attrgetter


def agg_totals(totals):
    totals = [_f for _f in totals if _f]
    n_files = len(totals)
    totals = list(map(_sum, zip(*totals)))
    if not totals:
        return ReportTotals.default_totals()
    totals = ReportTotals(*totals)
    totals.files = n_files
    totals.coverage = ratio(totals.hits, totals.lines) if totals.lines else None
    return totals


def sum_totals(totals):
    totals = [_f for _f in totals if _f]
    if not totals:
        return ReportTotals.default_totals()

    sessions = totals[0].sessions
    lines = sum(map(attrgetter("lines"), totals))
    hits = sum(map(attrgetter("hits"), totals))
    return ReportTotals(
        files=len(totals),
        lines=lines,
        hits=hits,
        misses=sum(map(attrgetter("misses"), totals)),
        partials=sum(map(attrgetter("partials"), totals)),
        branches=sum(map(attrgetter("branches"), totals)),
        methods=sum(map(attrgetter("methods"), totals)),
        messages=sum(map(attrgetter("messages"), totals)),
        coverage=ratio(hits, lines) if lines else None,
        sessions=sessions,
        complexity=sum(map(attrgetter("complexity"), totals)),
        complexity_total=sum(map(attrgetter("complexity_total"), totals)),
    )


def _sum(array):
    if array:
        if not isinstance(array[0], (type(None), str)):
            try:
                return sum(array)
            except:
                # https://sentry.io/codecov/v4/issues/159966549/
                return sum([a if type(a) is int else 0 for a in array])
    return None
