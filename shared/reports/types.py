from dataclasses import asdict, dataclass
from decimal import Decimal
from typing import Any, List, Optional, Sequence, Tuple, Union


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
        return iter(self.astuple())

    def astuple(self):
        return (
            self.files,
            self.lines,
            self.hits,
            self.misses,
            self.partials,
            self.coverage,
            self.branches,
            self.methods,
            self.messages,
            self.sessions,
            self.complexity,
            self.complexity_total,
            self.diff,
        )

    def asdict(self):
        return asdict(self)

    @classmethod
    def default_totals(cls):
        return cls(
            files=0,
            lines=0,
            hits=0,
            misses=0,
            partials=0,
            coverage=None,
            branches=0,
            methods=0,
            messages=0,
            sessions=0,
            complexity=0,
            complexity_total=0,
            diff=0,
        )


@dataclass
class NetworkFile(object):
    totals: ReportTotals
    session_totals: ReportTotals
    diff_totals: ReportTotals

    def astuple(self):
        return (
            self.totals.astuple(),
            [s.astuple() for s in self.session_totals] if self.session_totals else None,
            self.diff_totals.astuple() if self.diff_totals else None,
        )


@dataclass
class LineSession(object):
    __slots__ = ("id", "coverage", "branches", "partials", "complexity")
    id: int
    coverage: Decimal
    branches: int
    partials: Sequence[int]
    complexity: int

    def __init__(self, id, coverage, branches=None, partials=None, complexity=None):
        self.id = id
        self.coverage = coverage
        self.branches = branches
        self.partials = partials
        self.complexity = complexity

    def astuple(self):
        if self.branches is None and self.partials is None and self.complexity is None:
            return (self.id, self.coverage)
        return (self.id, self.coverage, self.branches, self.partials, self.complexity)


@dataclass
class CoverageDatapoint(object):
    __slots__ = ("sessionid", "coverage", "coverage_type", "labels")
    sessionid: int
    coverage: Decimal
    coverage_type: Optional[str]
    labels: List[str]

    def astuple(self):
        return (
            self.sessionid,
            self.coverage,
            self.coverage_type,
            self.labels,
        )

    def key_sorting_tuple(self):
        return (
            self.sessionid,
            str(self.coverage),
            self.coverage_type if self.coverage_type is not None else "",
            self.labels if self.labels is not None else [],
        )


@dataclass
class ReportLine(object):
    __slots__ = ("coverage", "type", "sessions", "messages", "complexity", "datapoints")
    coverage: Decimal
    type: str
    sessions: Sequence[LineSession]
    messages: List[str]
    complexity: Union[int, Tuple[int, int]]
    datapoints: Optional[List[CoverageDatapoint]]

    @classmethod
    def create(
        cls,
        coverage=None,
        type=None,
        sessions=None,
        messages=None,
        complexity=None,
        datapoints=None,
    ):
        return cls(
            coverage=coverage,
            type=type,
            sessions=sessions,
            messages=messages,
            complexity=complexity,
            datapoints=datapoints,
        )

    def astuple(self):
        return (
            self.coverage,
            self.type,
            [s.astuple() for s in self.sessions] if self.sessions else None,
            self.messages,
            self.complexity,
            [dt.astuple() for dt in self.datapoints] if self.datapoints else None,
        )

    def __post_init__(self):
        if self.sessions is not None:
            for i, sess in enumerate(self.sessions):
                if not isinstance(sess, LineSession) and sess is not None:
                    self.sessions[i] = LineSession(*sess)
        if self.datapoints is not None:
            for i, cov_dp in enumerate(self.datapoints):
                if not isinstance(cov_dp, CoverageDatapoint) and cov_dp is not None:
                    self.datapoints[i] = CoverageDatapoint(*cov_dp)


@dataclass
class ReportFileSummary(object):
    file_index: int
    file_totals: ReportTotals = None
    session_totals: Sequence[ReportTotals] = None
    diff_totals: Any = None

    def astuple(self):
        return (
            self.file_index,
            self.file_totals,
            self.session_totals,
            self.diff_totals,
        )


@dataclass
class Change(object):
    path: str = None
    new: bool = False
    deleted: bool = False
    in_diff: bool = None
    old_path: str = None
    totals: ReportTotals = None

    def __post_init__(self):
        if self.totals is not None:
            if not isinstance(self.totals, ReportTotals):
                self.totals = ReportTotals(*self.totals)


EMPTY = ""

TOTALS_MAP = tuple("fnhmpcbdMsCN")
