from dataclasses import dataclass
from decimal import Decimal
from typing import List, Optional, Sequence, Tuple, Union


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
