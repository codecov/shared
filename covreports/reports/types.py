from decimal import Decimal
from dataclasses import dataclass, astuple
from typing import Union, Tuple, Sequence


@dataclass
class ReportTotals(object):
    files: int = 0
    lines: int = 0
    hits: int = 0
    misses: int = 0
    partials: int = 0
    coverage: int = 0
    branches: int = 0
    methods: int = 0
    messages: int = 0
    sessions: int = 0
    complexity: int = 0
    complexity_total: int = 0
    diff: int = 0

    def __iter__(self):
        return iter(astuple(self))

    @classmethod
    def default_totals(cls):
        args = (0,) * 13
        return cls(*args)


@dataclass
class NetworkFile(object):
    totals: ReportTotals
    session_totals: ReportTotals
    diff_totals: ReportTotals


@dataclass
class LineSession(object):
    id: int
    coverage: Decimal
    branches: int = None
    partials: Sequence[int] = None
    complexity: int = None


@dataclass
class ReportLine(object):
    coverage: Decimal = None
    type: str = None
    sessions: LineSession = None
    messages: int = None
    complexity: Union[int, Tuple[int, int]] = None

    def __post_init__(self):
        if self.sessions is not None:
            for i, sess in enumerate(self.sessions):
                if not isinstance(sess, LineSession) and sess is not None:
                    self.sessions[i] = LineSession(*sess)


EMPTY = ""

TOTALS_MAP = tuple("fnhmpcbdMsCN")
