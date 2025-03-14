import dataclasses
import logging
from itertools import zip_longest
from typing import Any, cast

import orjson

from shared.reports.diff import DiffSegment, calculate_file_diff
from shared.reports.totals import get_line_totals
from shared.reports.types import EMPTY, ReportLine, ReportTotals
from shared.utils.merge import merge_all, merge_line

log = logging.getLogger(__name__)


class ReportFile:
    name: str
    _totals: ReportTotals | None
    diff_totals: ReportTotals | None
    _raw_lines: str | None
    _parsed_lines: list[None | str | ReportLine]
    _details: dict[str, Any]
    __present_sessions: set[int] | None

    def __init__(
        self,
        name: str,
        totals: ReportTotals | list | None = None,
        lines: list[None | str | ReportLine] | str | None = None,
        diff_totals: ReportTotals | list | None = None,
        ignore=None,
    ):
        """
        name = string, filename. "folder/name.py"
        totals = [0,1,0,...] (map out to one ReportTotals)
        lines = [] or string
           if [] then [null, line@1, null, line@3, line@4]
           if str then "\nline@1\n\nline@3"
           a line is [] that maps to ReportLine:obj
        ignore is for report buildling only, it filters out lines that should be not covered
            {eof:N, lines:[1,10]}
        """
        self.name = name
        self._totals = None
        self.diff_totals = None
        self._raw_lines = None
        self._parsed_lines = []
        self._details = {}
        self.__present_sessions = None

        if lines:
            if isinstance(lines, list):
                self._parsed_lines = lines
            else:
                self._raw_lines = lines

        self._ignore = _ignore_to_func(ignore) if ignore else None

        # The `_totals` and `__present_sessions` fields are cached values for the
        # `totals` and `_present_sessions` properties respectively.
        # The values are loaded at initialization time, or calculated from line data on-demand.
        # All mutating methods (like `append`, `merge`, etc) will either re-calculate these values
        # directly, or clear them so the `@property` accessors re-calculate them when needed.

        if isinstance(totals, ReportTotals):
            self._totals = totals
        elif totals:
            self._totals = ReportTotals(*totals)

        if isinstance(diff_totals, ReportTotals):
            self.diff_totals = diff_totals
        elif diff_totals:
            self.diff_totals = ReportTotals(*diff_totals)

    def _invalidate_caches(self):
        self._totals = None
        self.diff_totals = None
        self.__present_sessions = None

    @property
    def _lines(self):
        if self._raw_lines:
            self._parsed_lines = self._raw_lines.splitlines()
            detailsline = self._parsed_lines.pop(0)

            self._details = orjson.loads(detailsline or "null") or {}
            if present_sessions := self._details.get("present_sessions"):
                self.__present_sessions = set(present_sessions)

            self._raw_lines = None

        return self._parsed_lines

    @property
    def _present_sessions(self):
        _ensure_is_parsed = self._lines
        if self.__present_sessions is None:
            self.__present_sessions = set()
            for _, line in self.lines:
                self.__present_sessions.update(int(s.id) for s in line.sessions)
        return self.__present_sessions

    @property
    def details(self):
        _ensure_is_parsed = self._lines
        self._details["present_sessions"] = sorted(self._present_sessions)
        return self._details

    @property
    def totals(self):
        if not self._totals:
            self._totals = get_line_totals(line for _ln, line in self.lines)
        return self._totals

    def __repr__(self):
        try:
            return "<%s name=%s lines=%s>" % (
                self.__class__.__name__,
                self.name,
                len(self),
            )
        except Exception:
            return "<%s name=%s lines=n/a>" % (self.__class__.__name__, self.name)

    def _line(self, line: ReportLine | list | str):
        if isinstance(line, ReportLine):
            # line is already mapped to obj
            return line
        if isinstance(line, str):
            line = cast(list, orjson.loads(line))
        return ReportLine.create(*line)

    @property
    def lines(self):
        """Iter through lines with coverage
        returning (ln, line)
        <generator ((3, Line), (4, Line), (7, Line), ...)>
        """
        for ln, line in enumerate(self._lines, start=1):
            if line:
                yield ln, self._line(line)

    def calculate_diff(self, segments: list[DiffSegment]) -> ReportTotals:
        return calculate_file_diff(self, segments)

    def __iter__(self):
        """Iter through lines
        returning (line or None)
        <generator (None, Line, None, None, Line, ...)>
        """
        for line in self._lines:
            if line:
                yield self._line(line)
            else:
                yield None

    def __getitem__(self, ln):
        """Return a single line or None"""
        if ln == "totals":
            return self.totals
        if isinstance(ln, slice):
            return self._getslice(ln.start, ln.stop)
        if not isinstance(ln, int):
            raise TypeError("expecting type int got %s" % type(ln))
        elif ln < 1:
            raise ValueError("Line number must be greater then 0. Got %s" % ln)
        _line = self.get(ln)
        if not _line:
            raise IndexError("Line #%s not found in report" % ln)
        return _line

    def __setitem__(self, ln, line):
        """Append line to file, without merging if previously set"""
        if not isinstance(ln, int):
            raise TypeError("expecting type int got %s" % type(ln))
        elif not isinstance(line, ReportLine):
            raise TypeError("expecting type ReportLine got %s" % type(line))
        elif ln < 1:
            raise ValueError("Line number must be greater then 0. Got %s" % ln)
        elif self._ignore and self._ignore(ln):
            return

        length = len(self._lines)
        if length <= ln:
            self._lines.extend([EMPTY] * (ln - length))

        self._lines[ln - 1] = line
        self._invalidate_caches()
        return

    def __delitem__(self, ln: int):
        """Delete line from file"""
        if not isinstance(ln, int):
            raise TypeError("expecting type int got %s" % type(ln))
        elif ln < 1:
            raise ValueError("Line number must be greater then 0. Got %s" % ln)

        length = len(self._lines)
        if length <= ln:
            self._lines.extend([EMPTY] * (ln - length))

        self._lines[ln - 1] = EMPTY
        self._invalidate_caches()
        return

    def __len__(self):
        """Returns count(number of lines with coverage data)"""
        return sum(1 for _f in self._lines if _f)

    @property
    def eof(self):
        """Returns count(number of lines)"""
        return len(self._lines) + 1

    def _getslice(self, start, stop):
        """Returns a stream of lines between two indexes

        slice = report[5:25]


        for ln, line in report[5:25]:
            ...

        slice = report[5:25]
        assert slice is gernerator.
        list(slice) == [(1, Line), (2, Line)]

        NOTE: not be confused with the builtin function __getslice__ that was deprecated in python 3.x
        """
        for ln, line in enumerate(self._lines[start - 1 : stop - 1], start=start):
            if line:
                yield ln, self._line(line)

    def __contains__(self, ln):
        if not isinstance(ln, int):
            raise TypeError("expecting type int got %s" % type(ln))
        try:
            return self.get(ln) is not None
        except IndexError:
            return False

    def __bool__(self):
        return self.totals.lines > 0

    def get(self, ln):
        if not isinstance(ln, int):
            raise TypeError("expecting type int got %s" % type(ln))
        elif ln < 1:
            raise ValueError("Line number must be greater then 0. Got %s" % ln)

        try:
            line = self._lines[ln - 1]

        except IndexError:
            return None

        else:
            if line:
                return self._line(line)

    def append(self, ln, line):
        """Append a line to the report
        if the line exists it will merge it
        """
        if not isinstance(ln, int):
            raise TypeError("expecting type int got %s" % type(ln))
        elif not isinstance(line, ReportLine):
            raise TypeError("expecting type ReportLine got %s" % type(line))
        elif ln < 1:
            raise ValueError("Line number must be greater then 0. Got %s" % ln)
        elif self._ignore and self._ignore(ln):
            return False

        length = len(self._lines)
        if length <= ln:
            self._lines.extend([EMPTY] * (ln - length))
        _line = self.get(ln)
        if _line:
            self._lines[ln - 1] = merge_line(_line, line)
        else:
            self._lines[ln - 1] = line

        self._invalidate_caches()
        return True

    def merge(self, other_file, joined=True):
        """merges another report chunk
        returning the <dict totals>
        It's quicker to run the totals during processing
        """
        if other_file is None:
            return

        elif not isinstance(other_file, ReportFile):
            raise TypeError("expecting type ReportFile got %s" % type(other_file))

        if (
            self.name.endswith(".rb")
            and self.totals.lines == self.totals.misses
            and (
                other_file.totals.lines != self.totals.lines
                or other_file.totals.misses != self.totals.misses
            )
        ):
            # previous file was boil-the-ocean
            # OR previous file had END issue
            self._parsed_lines = other_file._lines.copy()
            self._raw_lines = None
            log.warning(
                "Doing something weird because of weird .rb logic",
                extra=dict(report_filename=self.name),
            )

        elif (
            self.name.endswith(".rb")
            and other_file.totals.lines == other_file.totals.misses
            and (
                other_file.totals.lines != self.totals.lines
                or other_file.totals.misses != self.totals.misses
            )
        ):
            # skip boil-the-ocean files
            # OR skip 0% coverage files because END issue
            return False

        else:
            # set new lines object
            self._parsed_lines = [
                merge_line(before, after, joined)
                for before, after in zip_longest(self, other_file)
            ]
            self._raw_lines = None

        self._invalidate_caches()
        return True

    def does_diff_adjust_tracked_lines(self, diff, future_file):
        for segment in diff["segments"]:
            # loop through each line
            pos = int(segment["header"][2]) or 1
            for line in segment["lines"]:
                if line[0] == "-":
                    if pos in self:
                        # tracked line removed
                        return True

                elif line[0] == "+":
                    if pos in future_file:
                        # tracked line added
                        return True
                    pos += 1
                else:
                    pos += 1
        return False

    def shift_lines_by_diff(self, diff, forward=True) -> None:
        """
        Adjusts report _lines IN PLACE to account for the diff given.
        !!! This WILL CHANGE the report permanently.

        Given coverage info for commit A (report._lines), and a diff from A to B (diff),
        adjust coverage info so that it works AS IF it was uploaded for commit B.
        """
        try:
            removed = "-"
            added = "+"
            # loop through each segment in the diff.
            for segment in diff["segments"]:
                # Header is [pos_in_base, lines_len_base, pos_in_head, lines_len_head]
                pos = (int(segment["header"][2]) or 1) - 1
                # loop through each line in segment
                for line in segment["lines"]:
                    if line[0] == removed:
                        if len(self._lines) > pos:
                            self._lines.pop(pos)
                    elif line[0] == added:
                        self._lines.insert(pos, "")
                        pos += 1
                    else:
                        pos += 1
        except (ValueError, KeyError, TypeError, IndexError):
            log.exception("Failed to shift lines by diff")
            pass
        self._invalidate_caches()

    @classmethod
    def line_without_labels(
        cls, line, session_ids_to_delete: set[int], label_ids_to_delete: set[int]
    ):
        new_datapoints = (
            [
                dp
                for dp in line.datapoints
                if dp.sessionid not in session_ids_to_delete
                or all(lb not in label_ids_to_delete for lb in dp.label_ids)
            ]
            if line.datapoints is not None
            else None
        )
        remaining_session_ids = set(dp.sessionid for dp in new_datapoints)
        removed_session_ids = session_ids_to_delete - remaining_session_ids
        if set(s.id for s in line.sessions) & removed_session_ids:
            new_sessions = [s for s in line.sessions if s.id not in removed_session_ids]
        else:
            new_sessions = line.sessions
        if len(new_sessions) == 0:
            return EMPTY
        remaining_coverages_from_datapoints = [s.coverage for s in new_datapoints]
        remaining_coverage_from_sessions_with_no_datapoints = [
            s.coverage for s in new_sessions if s.id not in remaining_session_ids
        ]

        new_coverage = merge_all(
            remaining_coverages_from_datapoints
            + remaining_coverage_from_sessions_with_no_datapoints
        )
        return dataclasses.replace(
            line,
            coverage=new_coverage,
            datapoints=new_datapoints,
            sessions=new_sessions,
        )

    def delete_labels(
        self,
        session_ids_to_delete: list[int] | set[int],
        label_ids_to_delete: list[int] | set[int],
    ):
        """
        Given a list of session_ids and label_ids to delete, remove all datapoints
        that belong to at least 1 session_ids to delete and include at least 1 of the label_ids to be removed.
        """
        session_ids_to_delete = set(session_ids_to_delete)
        label_ids_to_delete = set(label_ids_to_delete)
        for index, line in self.lines:
            if line.datapoints is not None:
                if any(
                    (
                        dp.sessionid in session_ids_to_delete
                        and label_id in label_ids_to_delete
                    )
                    for dp in line.datapoints
                    for label_id in dp.label_ids
                ):
                    # Line fits change requirements
                    new_line = self.line_without_labels(
                        line, session_ids_to_delete, label_ids_to_delete
                    )
                    if new_line == EMPTY:
                        del self[index]
                    else:
                        self[index] = new_line

        self._invalidate_caches()

    @classmethod
    def line_without_multiple_sessions(
        cls, line: ReportLine, session_ids_to_delete: set[int]
    ):
        new_sessions = [s for s in line.sessions if s.id not in session_ids_to_delete]
        if len(new_sessions) == 0:
            return EMPTY

        new_datapoints = (
            [dt for dt in line.datapoints if dt.sessionid not in session_ids_to_delete]
            if line.datapoints is not None
            else None
        )
        remaining_coverages = [s.coverage for s in new_sessions]
        new_coverage = merge_all(remaining_coverages)
        return dataclasses.replace(
            line,
            sessions=new_sessions,
            coverage=new_coverage,
            datapoints=new_datapoints,
        )

    def delete_multiple_sessions(self, session_ids_to_delete: set[int]):
        current_sessions = self._present_sessions
        new_sessions = current_sessions.difference(session_ids_to_delete)
        if current_sessions == new_sessions:
            return  # nothing to do

        self._invalidate_caches()

        if not new_sessions:
            # no remaining sessions means no line data
            self._parsed_lines = []
            self._raw_lines = None
            return

        for index, line in self.lines:
            if any(s.id in session_ids_to_delete for s in line.sessions):
                new_line = self.line_without_multiple_sessions(
                    line, session_ids_to_delete
                )
                if new_line == EMPTY:
                    del self[index]
                else:
                    self[index] = new_line

        self.__present_sessions = new_sessions


def _ignore_to_func(ignore):
    """Returns a function to determine whether a a line should be saved to the ReportFile

    This function returns a function, that is called with an int parameter: which is the line number

    Args:
        ignore: A dict, with a structure similar to
            {
                'eof': 41,
                'lines': {40, 33, 37, 38}
            }

    Returns:
        A function, which takes an int as first parameter and returns a boolean
    """
    eof = ignore.get("eof")
    lines = ignore.get("lines") or []
    if eof:
        if isinstance(eof, str):
            # Sometimes eof is 'N', not sure which cases
            return lambda ln: str(ln) > eof or ln in lines
        # This means the eof as a number: the last line of the file and
        # anything after that should be ignored
        return lambda ln: ln > eof or ln in lines
    else:
        return lambda ln: ln in lines
