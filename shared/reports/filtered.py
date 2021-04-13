import dataclasses

from shared.utils.totals import agg_totals, sum_totals
from shared.utils.make_network_file import make_network_file
from shared.utils.match import match, match_any
from shared.reports.types import ReportTotals, EMPTY
from shared.helpers.numeric import ratio
from shared.utils.merge import line_type, merge_all
from shared.metrics import metrics


class FilteredReportFile(object):

    __slots__ = ["report_file", "session_ids", "_totals"]

    def __init__(self, report_file, session_ids):
        self.report_file = report_file
        self.session_ids = session_ids
        self._totals = None

    def line_modifier(self, line):
        new_sessions = [s for s in line.sessions if s.id in self.session_ids]
        remaining_coverages = [s.coverage for s in new_sessions]
        if len(new_sessions) == 0:
            return EMPTY
        new_coverage = merge_all(remaining_coverages)
        return dataclasses.replace(line, sessions=new_sessions, coverage=new_coverage)

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
        for ln, line in self.report_file.lines:
            line = self.line_modifier(line)
            if line:
                yield ln, line

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
        """return dict of totals
        """
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
        ) or (0, 0,)

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

    def file_reports(self):
        for f in self.files:
            yield self.get(f)

    @property
    def session_ids_to_include(self):
        if self._sessions_to_include is None:
            if not self.flags:
                self._sessions_to_include = set(self.report.sessions.keys())
            else:
                self._sessions_to_include = set(
                    sid
                    for (sid, session) in self.report.sessions.items()
                    if match_any(self.flags, session.flags)
                )
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
        return FilteredReportFile(r, self.session_ids_to_include)

    @property
    def files(self):
        return [f for f in self.report.files if self.should_include(f)]

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
                yield self.get(filename).totals

    @metrics.timer("shared.reports.filtered._process_totals")
    def _process_totals(self):
        """Runs through the file network to aggregate totals
        returns <ReportTotals>
        """
        totals = agg_totals(self._iter_totals())
        totals.sessions = len(self.session_ids_to_include)

        return ReportTotals(*tuple(totals))

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
