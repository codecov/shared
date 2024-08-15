import logging
from dataclasses import asdict, dataclass
from decimal import Decimal
from typing import Any, Dict, List, Optional, Sequence, Tuple, TypedDict, Union

from shared.config import get_config

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


class SessionTotalsArray(object):
    def __init__(self, session_count=0, non_null_items=None):
        self.session_count: int = session_count

        parsed_non_null_items = {}
        if non_null_items is None:
            non_null_items = {}
        for key, value in non_null_items.items():
            if isinstance(value, SessionTotals):
                parsed_non_null_items[key] = value
            elif isinstance(value, list):
                parsed_non_null_items[key] = SessionTotals(*value)
            else:
                log.warning(
                    "Unknown value for SessionTotal. Ignoring.",
                    extra=dict(session_total=value, key=key),
                    stack_info=True,
                )
        self.non_null_items: Dict[int, SessionTotals] = parsed_non_null_items

    @classmethod
    def build_from_encoded_data(cls, sessions_array: Any):
        if isinstance(sessions_array, dict):
            # The session_totals array is already encoded in the new format
            if "meta" not in sessions_array:
                # This shouldn't happen, but it would be a good indication that processing is not as we expect
                log.warning(
                    "meta info not found in encoded SessionArray",
                    extra=dict(sessions_array=sessions_array),
                )
                sessions_array["meta"] = {
                    "session_count": int(max(sessions_array.keys())) + 1
                }
            meta_info = sessions_array.get("meta")
            session_count = meta_info["session_count"]
            # Force keys to be integers for standarization.
            # It probably becomes a strong when going to the database
            non_null_items = {
                int(key): value
                for key, value in sessions_array.items()
                if key != "meta"
            }
            return cls(session_count=session_count, non_null_items=non_null_items)
        elif isinstance(sessions_array, list):
            session_count = len(sessions_array)
            non_null_items = {}
            for idx, session_totals in enumerate(sessions_array):
                if session_totals is not None:
                    non_null_items[idx] = session_totals
            return cls(session_count=session_count, non_null_items=non_null_items)
        elif isinstance(sessions_array, cls):
            return sessions_array
        elif sessions_array is None:
            return SessionTotalsArray()
        log.warning(
            "Tried to build SessionArray from unknown encoded data.",
            extra=dict(data=sessions_array, data_type=type(sessions_array)),
        )
        return None

    def to_database(self):
        if get_config("setup", "legacy_report_style", default=False):
            return [
                value.to_database() if value is not None else None for value in self
            ]
        encoded_obj = {
            key: value.to_database() for key, value in self.non_null_items.items()
        }
        encoded_obj["meta"] = dict(session_count=self.session_count)
        return encoded_obj

    def __repr__(self) -> str:
        return f"SessionTotalsArray<session_count={self.session_count}, non_null_items={self.non_null_items}>"

    def __iter__(self):
        """
        Expands SessionTotalsArray back to the legacy format
        e.g. [None, None, ReportTotals, None, ReportTotals]
        """
        for idx in range(self.session_count):
            if idx in self.non_null_items:
                yield self.non_null_items[idx]
            else:
                yield None

    def __eq__(self, value: object) -> bool:
        if isinstance(value, SessionTotalsArray):
            return (
                self.session_count == value.session_count
                and self.non_null_items == value.non_null_items
            )
        return False

    def __bool__(self):
        return self.session_count > 0

    def append(self, totals: SessionTotals | None):
        if totals is None:
            log.warning("Trying to append None session total to SessionTotalsArray")
            return
        new_totals_index = self.session_count
        self.non_null_items[new_totals_index] = totals
        self.session_count += 1

    def delete_many(self, indexes_to_delete: List[int]):
        deleted_items = [self.delete(index) for index in indexes_to_delete]
        return deleted_items

    def delete(self, index_to_delete: Union[int, str]):
        return self.non_null_items.pop(int(index_to_delete), None)


@dataclass
class NetworkFile(object):
    totals: ReportTotals
    session_totals: SessionTotalsArray
    diff_totals: ReportTotals

    def __init__(
        self, totals=None, session_totals=None, diff_totals=None, *args, **kwargs
    ) -> None:
        self.totals = totals
        self.session_totals = SessionTotalsArray.build_from_encoded_data(session_totals)
        self.diff_totals = diff_totals

    def astuple(self):
        return (
            self.totals.astuple(),
            self.session_totals.to_database(),
            self.diff_totals.astuple() if self.diff_totals else None,
        )


class ReportHeader(TypedDict):
    labels_index: Dict[int, str]


@dataclass
class ReportFileSummary(object):
    file_index: int
    file_totals: ReportTotals = None
    session_totals: SessionTotalsArray = None
    diff_totals: Any = None

    def __init__(
        self,
        file_index,
        file_totals=None,
        session_totals=None,
        diff_totals=None,
        *args,
        **kwargs,
    ) -> None:
        self.file_index = file_index
        self.file_totals = file_totals
        self.diff_totals = diff_totals
        self.session_totals = SessionTotalsArray.build_from_encoded_data(session_totals)

    def astuple(self):
        return (
            self.file_index,
            self.file_totals,
            self.session_totals,
            self.diff_totals,
        )
