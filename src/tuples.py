from collections import namedtuple

NetworkFile = namedtuple('NetworkFile', [
    'totals',          # 0
    'session_totals',  # 1
    'diff_totals'      # 2
])

ReportTotals = namedtuple('ReportTotals', [
    'files',             # 0
    'lines',             # 1
    'hits',              # 2
    'misses',            # 3
    'partials',          # 4
    'coverage',          # 5
    'branches',          # 6
    'methods',           # 7
    'messages',          # 8
    'sessions',          # 9
    'complexity',        # 10
    'complexity_total',  # 11
    'diff'               # 12, a <ReportTotals> obj
])
ReportTotals.__new__.__defaults__ = (0,) * len(ReportTotals._fields)

ReportLine = namedtuple('ReportLine', [
    'coverage',
    'type',
    'sessions',
    'messages',
    'complexity'  # [int | tuple(int, int)]
])
ReportLine.__new__.__defaults__ = (None,) * len(ReportLine._fields)

LineSession = namedtuple('LineSession', [
    'id',
    'coverage',
    'branches',
    'partials',
    'complexity'
])
LineSession.__new__.__defaults__ = (None,) * len(LineSession._fields)

EMPTY = ''

TOTALS_MAP = tuple('fnhmpcbdMsCN')
