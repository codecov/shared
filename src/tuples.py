from collections import namedtuple

NetworkFile = namedtuple('NetworkFile', [
    'totals',          # 0
    'session_totals',  # 1
    'diff_totals'      # 2
])
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
