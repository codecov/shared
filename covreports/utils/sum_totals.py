from covreports.utils.tuples import ReportTotals
from covreports.helpers.ratio import ratio
from operator import itemgetter


def sum_totals(totals):
    totals = filter(None, totals)
    if not totals:
        return ReportTotals()

    sessions = totals[0][9]
    lines = sum(map(itemgetter(1), totals))
    hits = sum(map(itemgetter(2), totals))
    return ReportTotals(files=len(totals),
                        lines=lines,
                        hits=hits,
                        misses=sum(map(itemgetter(3), totals)),
                        partials=sum(map(itemgetter(4), totals)),
                        branches=sum(map(itemgetter(6), totals)),
                        methods=sum(map(itemgetter(7), totals)),
                        messages=sum(map(itemgetter(8), totals)),
                        coverage=ratio(hits, lines),
                        sessions=sessions,
                        complexity=sum(map(itemgetter(10), totals)),
                        complexity_total=sum(map(itemgetter(11), totals)))
