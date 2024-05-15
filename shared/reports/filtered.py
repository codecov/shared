import dataclasses
import logging
import os

from shared.config import get_config
from shared.helpers.numeric import ratio
from shared.metrics import metrics
from shared.reports.types import EMPTY, ReportTotals
from shared.utils.make_network_file import make_network_file
from shared.utils.match import match, match_any
from shared.utils.merge import get_complexity_from_sessions, line_type, merge_all
from shared.utils.totals import agg_totals, sum_totals

log = logging.getLogger(__name__)


def _contain_any_of_the_flags(expected_flags, actual_flags):
    if expected_flags is None or actual_flags is None:
        return False
    return len(set(expected_flags) & set(actual_flags)) > 0


class FilteredReportFile(object):
    __slots__ = ["report_file", "session_ids", "_totals", "_cached_lines"]

    def __init__(self, report_file, session_ids):
        self.report_file = report_file
        self.session_ids = session_ids
        self._totals = None
        self._cached_lines = None

    def line_modifier(self, line):
        new_sessions = [s for s in line.sessions if s.id in self.session_ids]
        new_datapoints = (
            [dp for dp in line.datapoints if dp.sessionid in self.session_ids]
            if line.datapoints is not None
            else None
        )
        remaining_coverages = [s.coverage for s in new_sessions]
        if len(new_sessions) == 0:
            return EMPTY
        new_coverage = merge_all(remaining_coverages)
        return dataclasses.replace(
            line,
            complexity=get_complexity_from_sessions(new_sessions),
            sessions=new_sessions,
            coverage=new_coverage,
            datapoints=new_datapoints,
        )

    @property
    def name(self):
        return self.report_file.name

    @property
    def totals(self):
        if not self._totals:
            self._totals = self._process_totals()
        return self._totals

    @property
    def eof(self):
        return self.report_file.eof

    @property
    def lines(self):
        """Iter through lines with coverage
        returning (ln, line)
        <generator ((3, Line), (4, Line), (7, Line), ...)>
        """
        if self._cached_lines:
            return self._cached_lines
        ret = []
        for ln, line in self.report_file.lines:
            line = self.line_modifier(line)
            if line:
                ret.append((ln, line))
        self._cached_lines = ret
        return ret

    def calculate_diff(self, all_file_segments):
        fg = self.get
        lines = []
        le = lines.extend
        # add all new lines data to a new file to get totals
        [
            le(
                [
                    (i, fg(i))
                    for i, line in enumerate(
                        [l for l in segment["lines"] if l[0] != "-"],
                        start=int(segment["header"][2]) or 1,
                    )
                    if line[0] == "+"
                ]
            )
            for segment in all_file_segments
        ]
        lines = [l for l in lines if l[1] is not None]
        return self.calculate_totals_from_lines(lines)

    def get(self, ln):
        line = self.report_file.get(ln)
        if line:
            line = self.line_modifier(line)
            if not line:
                return None
            return line

    def _process_totals(self):
        """return dict of totals"""
        return self.calculate_totals_from_lines(self.lines)

    @classmethod
    def sum_of_complexity(cls, l):
        # (hit, total)
        c = l[1].complexity
        if not c:
            # no coverage data provided
            return (0, 0)
        elif type(c) is int:
            # coverage is of type int
            return (c, 0)
        else:
            # coverage is ratio
            return c

    @classmethod
    def calculate_totals_from_lines(cls, inputted_lines):
        inputted_lines = list(inputted_lines)
        cov, types, messages = [], [], []
        _cov, _types, _messages = cov.append, types.append, messages.append
        for ln, line in inputted_lines:
            _cov(line_type(line.coverage))
            _types(line.type)
            _messages(len(line.messages or []))
        hits = cov.count(0)
        misses = cov.count(1)
        partials = cov.count(2)
        lines = hits + misses + partials

        complexity = tuple(
            map(sum, zip(*map(cls.sum_of_complexity, inputted_lines)))
        ) or (0, 0)

        return ReportTotals(
            files=0,
            lines=lines,
            hits=hits,
            misses=misses,
            partials=partials,
            coverage=ratio(hits, lines) if lines else None,
            branches=types.count("b"),
            methods=types.count("m"),
            messages=sum(messages),
            sessions=0,
            complexity=complexity[0],
            complexity_total=complexity[1],
        )


class FilteredReport(object):
    def __init__(self, report, path_patterns, flags):
        self.report = report
        self.path_patterns = path_patterns
        self.flags = flags
        self._totals = None
        self._sessions_to_include = None
        self.report_file_cache = {}

    def file_reports(self):
        for f in self.files:
            yield self.get(f)

    def has_precalculated_totals(self):
        return self._totals is not None

    def _calculate_sessionids_to_include(self):
        if not self.flags:
            return set(self.report.sessions.keys())
        old_style_sessions = set(
            sid
            for (sid, session) in self.report.sessions.items()
            if match_any(self.flags, session.flags)
        )
        new_style_sessions = set(
            sid
            for (sid, session) in self.report.sessions.items()
            if _contain_any_of_the_flags(self.flags, session.flags)
        )
        if old_style_sessions != new_style_sessions:
            log.info(
                "New result would differ from old result",
                extra=dict(
                    old_result=sorted(old_style_sessions),
                    new_result=sorted(new_style_sessions),
                    filter_flags=sorted(self.flags),
                    report_flags=sorted(self.report.flags.keys()),
                ),
            )
        if get_config("compatibility", "flag_pattern_matching", default=False):
            return old_style_sessions
        return new_style_sessions

    @property
    def session_ids_to_include(self):
        if self._sessions_to_include is None:
            self._sessions_to_include = self._calculate_sessionids_to_include()
        return self._sessions_to_include

    def should_include(self, filename):
        return match(self.path_patterns, filename)

    @property
    def network(self):
        for fname, data in self.report._files.items():
            file = self.get(fname)
            if file:
                yield fname, make_network_file(file.totals)

    def get(self, filename, _else=None):
        if not self.should_include(filename):
            return _else
        if not self.flags:
            return self.report.get(filename)
        r = self.report.get(filename)
        if r is None:
            return None

        if filename not in self.report_file_cache:
            self.report_file_cache[filename] = FilteredReportFile(
                r, self.session_ids_to_include
            )
        return self.report_file_cache[filename]

    @property
    def files(self):
        return [f for f in self.report.files if self.should_include(f)]

    def get_file_totals(self, path):
        if self.should_include(path):
            return self.report.get_file_totals(path)

        return None

    @property
    def manifest(self):
        return self.files

    @property
    def totals(self):
        if not self._totals:
            self._totals = self._process_totals()
        return self._totals

    def is_empty(self):
        return not any(self.should_include(x) for x in self.report._files.keys())

    def _iter_totals(self):
        for filename, data in self.report._files.items():
            if self.should_include(filename):
                res = self.get(filename).totals
                if res and res.lines > 0:
                    yield res

    def _can_use_session_totals(self):
        a = os.getenv("CORRECT_SESSION_TOTALS_SINCE")
        if a is None:
            return False
        if len(self.session_ids_to_include) != 1:
            return False
        if self.path_patterns:
            return False
        only_session_id = list(self.session_ids_to_include)[0]
        only_session_to_use = self.report.sessions[only_session_id]
        if only_session_to_use is not None and only_session_to_use.time is not None:
            return (
                only_session_to_use.time > int(a)
                and only_session_to_use.totals is not None
            )
        return False

    @metrics.timer("shared.reports.filtered._process_totals")
    def _process_totals(self):
        """Runs through the file network to aggregate totals
        returns <ReportTotals>
        """
        totals = agg_totals(self._iter_totals())
        totals.sessions = len(self.session_ids_to_include)
        res = ReportTotals(*tuple(totals))
        try:
            if self._can_use_session_totals():
                only_session_id = list(self.session_ids_to_include)[0]
                if self.report.sessions.get(only_session_id):
                    only_session_to_use = self.report.sessions[only_session_id]
                    session_totals = only_session_to_use.totals
                    if session_totals is not None:
                        session_totals.sessions = 1
                        if session_totals == res:
                            log.info("Could have used the original sessions totals")
                        elif (
                            session_totals.coverage != res.coverage
                            or session_totals.hits != res.hits
                        ):
                            log.info(
                                "There is a coverage difference between original session and calculated totals",
                                extra=dict(
                                    original_totals=session_totals.asdict()
                                    if session_totals is not None
                                    else None,
                                    calculated_totals=res.asdict()
                                    if res is not None
                                    else None,
                                    session_time=only_session_to_use.time,
                                    flags=self.flags,
                                ),
                            )
                        else:
                            log.info(
                                "There is a general difference between original session and calculated totals",
                                extra=dict(
                                    original_totals=session_totals.asdict()
                                    if session_totals is not None
                                    else None,
                                    calculated_totals=res.asdict()
                                    if res is not None
                                    else None,
                                ),
                            )
        except Exception:
            log.warning(
                "Unable to calculate single-session totals",
                extra=dict(flags=self.flags, path_patterns=self.path_patterns),
                exc_info=True,
            )
        return res

    def calculate_diff(self, diff):
        file_dict = {}
        if diff and diff.get("files"):
            list_of_file_totals = []
            for path, data in diff["files"].items():
                if data["type"] in ("modified", "new"):
                    _file = self.get(path)
                    if _file:
                        file_totals = _file.calculate_diff(data["segments"])
                        file_dict[path] = file_totals
                        list_of_file_totals.append(file_totals)

            totals = sum_totals(list_of_file_totals)

            if totals.lines == 0:
                totals = dataclasses.replace(
                    totals, coverage=None, complexity=None, complexity_total=None
                )

            return {"general": totals, "files": file_dict}
        return None

    def apply_diff(self, diff, _save=True):
        """
        Add coverage details to the diff at ['coverage'] = <ReportTotals>
        returns <ReportTotals>
        """
        if not diff or not diff.get("files"):
            return None
        totals = self.calculate_diff(diff)
        if _save and totals:
            self.save_diff_calculation(diff, totals)
        return totals.get("general")

    def save_diff_calculation(self, diff, diff_result):
        diff["totals"] = diff_result["general"]
        self.diff_totals = diff["totals"]
        for filename, file_totals in diff_result["files"].items():
            data = diff["files"].get(filename)
            data["totals"] = file_totals

    def __iter__(self):
        """Iter through all the files
        yielding <ReportFile>
        """
        for file in self.report:
            if self.should_include(file.name):
                if not self.flags:
                    yield file
                else:
                    yield FilteredReportFile(file, self.session_ids_to_include)
