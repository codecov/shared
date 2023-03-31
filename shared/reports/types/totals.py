import logging
from dataclasses import asdict, dataclass
from typing import Dict, Union

log = logging.getLogger(__name__)


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


SessionTotals = ReportTotals


class SessionTotalsArray(object):
    def __init__(self, real_length=0, non_null_items=dict()):
        self.real_length: int = real_length
        self.non_null_items: Dict[int, SessionTotals] = non_null_items

    @classmethod
    def build_from_encoded_data(cls, sessions_array: Union[dict, list]):
        session_array_object = SessionTotalsArray()
        if isinstance(sessions_array, dict):
            # The session_totals array is already encoded in the new format
            if "meta" not in sessions_array:
                # This shouldn't happen, but it would be a good indication that processing is not as we expect
                log.warning(
                    "meta info not found in encoded SessionArray",
                    extra=dict(sessions_array=sessions_array),
                )
                sessions_array["meta"] = {"real_length": max(sessions_array.keys()) + 1}
            meta_info = sessions_array.pop("meta")
            session_array_object.real_length = meta_info["real_length"]
            # Force keys to be integers for standarization.
            # It probably becomes a strong when going to the database
            session_array_object.non_null_items = {
                int(key): value for key, value in sessions_array.items()
            }
            return session_array_object
        elif isinstance(sessions_array, list):
            session_array_object.real_length = len(sessions_array)
            non_null_items = {}
            for idx, session_totals in enumerate(sessions_array):
                if session_totals is not None:
                    non_null_items[idx] = session_totals
            session_array_object.non_null_items = non_null_items
            return session_array_object
        elif isinstance(sessions_array, cls):
            return sessions_array
        elif sessions_array is None:
            return SessionTotalsArray()
        log.warning(
            "Tried to build SessionArray from unknown encoded data.",
            dict(data=sessions_array, data_type=type(sessions_array)),
        )
        return None

    def to_database(self):
        encoded_obj = dict()
        encoded_obj["meta"] = dict(real_length=self.real_length)
        encoded_obj.update(self.non_null_items)
        return encoded_obj

    def __repr__(self) -> str:
        return f"SessionTotalsArray<real_length={self.real_length}, non_null_items={self.non_null_items}>"

    def __iter__(self):
        # We need to iterate in the correct order of sessions
        ordered_sessions = sorted(self.non_null_items.keys())
        for session_idx in ordered_sessions:
            yield self.non_null_items[session_idx]

    def __eq__(self, value: object) -> bool:
        if isinstance(value, SessionTotalsArray):
            return (
                self.real_length == value.real_length
                and self.non_null_items == value.non_null_items
            )
        return False

    def __bool__(self):
        return self.real_length > 0

    def append(self, totals: SessionTotals):
        if totals == None:
            log.warning("Trying to append None session total to SessionTotalsArray")
            return
        new_totals_index = self.real_length
        self.non_null_items[new_totals_index] = totals
        self.real_length += 1
