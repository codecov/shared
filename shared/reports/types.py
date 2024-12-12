import logging
from dataclasses import asdict, dataclass
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Sequence, Tuple, TypedDict, Union

log = logging.getLogger(__name__)


@dataclass
class ReportTotals(object):
    files: int = 0
    lines: int = 0
    hits: int = 0
    misses: int = 0
    partials: int = 0
    # The coverage is a string of a float that's rounded to 5 decimal places (or "100", "0")
    # i.e. "98.76543", "100", "0" are all valid.
    coverage: Optional[str] = 0
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

    def to_database(self):
        obj = list(self)
        while obj and obj[-1] in ("0", 0):
            obj.pop()
        return obj

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
class LineSession(object):
    __slots__ = ("id", "coverage", "branches", "partials", "complexity")
    id: int
    coverage: Decimal
    branches: list[int] | None
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
    __slots__ = ("sessionid", "coverage", "coverage_type", "label_ids")
    sessionid: int
    coverage: Decimal
    coverage_type: Optional[str]
    label_ids: List[int]

    def astuple(self):
        return (
            self.sessionid,
            self.coverage,
            self.coverage_type,
            self.label_ids,
        )

    def __post_init__(self):
        if self.label_ids is not None:

            def possibly_cast_to_int(el):
                return int(el) if isinstance(el, str) and el.isnumeric() else el

            self.label_ids = [possibly_cast_to_int(el) for el in self.label_ids]

    def key_sorting_tuple(self):
        return (
            self.sessionid,
            str(self.coverage),
            self.coverage_type if self.coverage_type is not None else "",
            self.label_ids if self.label_ids is not None else [],
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


SessionTotals = ReportTotals


@dataclass
class NetworkFile(object):
    totals: ReportTotals
    diff_totals: ReportTotals

    def __init__(self, totals=None, diff_totals=None, *args, **kwargs) -> None:
        self.totals = totals
        self.diff_totals = diff_totals

    def astuple(self):
        return (
            self.totals.astuple(),
            # Placeholder for deprecated/broken `session_totals` field.
            # Old reports had a map of session ID to per-session totals here,
            # but they weren't used and a bug caused them to bloat wildly.
            None,
            self.diff_totals.astuple() if self.diff_totals else None,
        )


class ReportHeader(TypedDict):
    labels_index: Dict[int, str]


@dataclass
class ReportFileSummary(object):
    file_index: int
    file_totals: ReportTotals = None
    diff_totals: Any = None

    def __init__(
        self,
        file_index,
        file_totals=None,
        diff_totals=None,
        *args,
        **kwargs,
    ) -> None:
        self.file_index = file_index
        self.file_totals = file_totals
        self.diff_totals = diff_totals

    def astuple(self):
        return (
            self.file_index,
            self.file_totals,
            # Placeholder for deprecated/broken `session_totals` field.
            # Old reports had a map of session ID to per-session totals here,
            # but they weren't used and a bug caused them to bloat wildly.
            None,
            self.diff_totals,
        )


class UploadType(Enum):
    COVERAGE = "coverage"
    TEST_RESULTS = "test_results"
    BUNDLE_ANALYSIS = "bundle_analysis"
