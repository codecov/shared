from copy import copy
from itertools import zip_longest, filterfalse
import logging
from json import loads, dumps, JSONEncoder
import dataclasses
from typing import Sequence, Any

from shared.helpers.yaml import walk
from shared.helpers.flag import Flag
from shared.helpers.numeric import ratio
from shared.helpers.zfill import zfill
from shared.utils.ReportEncoder import ReportEncoder
from shared.utils.totals import agg_totals, sum_totals
from shared.utils.flare import report_to_flare
from shared.utils.make_network_file import make_network_file
from shared.utils.match import match, match_any
from shared.utils.merge import (
    merge_line,
    line_type,
    get_coverage_from_sessions,
    get_complexity_from_sessions,
)
from shared.utils.migrate import migrate_totals
from shared.utils.sessions import Session
from shared.reports.types import (
    ReportTotals,
    ReportLine,
    LineSession,
    EMPTY,
    TOTALS_MAP,
    ReportFileSummary,
)

log = logging.getLogger(__name__)


def unique_everseen(iterable):
    "List unique elements, preserving order. Remember all elements ever seen."
    # unique_everseen('AAAABBBCCDAABBB') --> A B C D
    # unique_everseen('ABBCcAD', str.lower) --> A B C D
    seen = set()
    seen_add = seen.add
    for element in filterfalse(seen.__contains__, iterable):
        seen_add(element)
        yield element


END_OF_CHUNK = "\n<<<<< end_of_chunk >>>>>\n"


class ReportFile(object):
    __slot__ = (
        "name",
        "_details",
        "_lines",
        "_line_modifier",
        "_ignore",
        "_totals",
        "_session_totals",
    )

    def __init__(
        self,
        name,
        totals=None,
        session_totals=None,
        lines=None,
        line_modifier=None,
        ignore=None,
    ):
        """
        name = string, filename. "folder/name.py"
        totals = [0,1,0,...] (map out to one ReportTotals)
        session_totals = [[],[]] (map to list of Session())
        lines = [] or string
           if [] then [null, line@1, null, line@3, line@4]
           if str then "\nline@1\n\nline@3"
           a line is [] that maps to ReportLine:obj
        line_modifier = function, filter lines by sessions.
        ignore is for report buildling only, it filters out lines that should be not covered
            {eof:N, lines:[1,10]}
        """
        self.name = name
        # lines = [<details dict()>, <Line #1>, ....]
        if lines:
            if type(lines) is list:
                self._details = None
                self._lines = lines

            else:
                lines = lines.splitlines()
                self._details = loads(lines.pop(0) or "null")
                self._lines = lines
        else:
            self._details = {}
            self._lines = []

        # <line_modifier callable>
        self._line_modifier = line_modifier
        self._ignore = _ignore_to_func(ignore) if ignore else None

        if line_modifier:
            self._totals = None  # need to reprocess these
        else:
            # totals = <ReportTotals []>
            if isinstance(totals, ReportTotals):
                self._totals = totals
            else:
                self._totals = ReportTotals(*totals) if totals else None

        self._session_totals = session_totals

    def __repr__(self):
        try:
            return "<%s name=%s lines=%s>" % (
                self.__class__.__name__,
                self.name,
                len(self),
            )
        except:
            return "<%s name=%s lines=n/a>" % (self.__class__.__name__, self.name)

    def _line(self, line):
        if isinstance(line, ReportLine):
            # line is already mapped to obj
            return line
        elif type(line) is list:
            # line needs to be mapped to ReportLine
            # line = [1, 'b', [], null, null] = ReportLine()
            return ReportLine(*line)
        else:
            # these are old versions
            line = loads(line)
            if len(line) > 2 and line[2]:
                line[2] = [
                    LineSession(*tuple(session)) for session in line[2] if session
                ]
            return ReportLine(*line)

    @property
    def lines(self):
        """Iter through lines with coverage
        returning (ln, line)
        <generator ((3, Line), (4, Line), (7, Line), ...)>
        """
        func = self._line_modifier
        for ln, line in enumerate(self._lines, start=1):
            if line:
                line = self._line(line)
                if func:
                    line = func(line)
                    if not line:
                        continue
                yield ln, line

    def __iter__(self):
        """Iter through lines
        returning (line or None)
        <generator (None, Line, None, None, Line, ...)>
        """
        func = self._line_modifier
        for line in self._lines:
            if line:
                line = self._line(line)
                if func:
                    line = func(line)
                    if not line:
                        yield None
                yield line
            else:
                yield None

    def ignore_lines(self, lines=None, eof=None):
        if lines:
            _len = len(self._lines)
            for ln in lines:
                if ln <= _len:
                    self._lines[ln - 1] = None
        if eof:
            self._lines = self._lines[:eof]
        self._totals = None

    def __getitem__(self, ln):
        """Return a single line or None
        """
        if ln == "totals":
            return self.totals
        if type(ln) is slice:
            return self._getslice(ln.start, ln.stop)
        if not type(ln) is int:
            raise TypeError("expecting type int got %s" % type(ln))
        elif ln < 1:
            raise ValueError("Line number must be greater then 0. Got %s" % ln)
        _line = self.get(ln)
        if not _line:
            raise IndexError("Line #%s not found in report" % ln)
        return _line

    def __setitem__(self, ln, line):
        """Append line to file, without merging if previously set
        """
        if not type(ln) is int:
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
        return

    def __len__(self):
        """Returns count(number of lines with coverage data)
        """
        return len([_f for _f in self._lines if _f])

    @property
    def eof(self):
        """Returns count(number of lines)
        """
        return len(self._lines) + 1

    def _getslice(self, start, stop):
        """Retrns a stream of lines between two indexes

        slice = report[5:25]


        for ln, line in report[5:25]:
            ...

        slice = report[5:25]
        assert slice is gernerator.
        list(slice) == [(1, Line), (2, Line)]

        NOTE: not be confused with the builtin function __getslice__ that was deprecated in python 3.x
        """
        func = self._line_modifier
        for ln, line in enumerate(self._lines[start - 1 : stop - 1], start=start):
            if line:
                line = self._line(line)
                if func:
                    line = func(line)
                    if not line:
                        continue
                yield ln, line

    def __contains__(self, ln):
        if not type(ln) is int:
            raise TypeError("expecting type int got %s" % type(ln))
        try:
            return self.get(ln) is not None
        except IndexError:
            return False

    def __bool__(self):
        return self.totals.lines > 0

    def get(self, ln):
        if not type(ln) is int:
            raise TypeError("expecting type int got %s" % type(ln))
        elif ln < 1:
            raise ValueError("Line number must be greater then 0. Got %s" % ln)

        try:
            line = self._lines[ln - 1]

        except IndexError:
            return None

        else:
            if line:
                func = self._line_modifier
                line = self._line(line)
                if func:
                    # need to filter this line by sessions
                    line = func(line)
                    if not line:
                        return None
                return line

    def append(self, ln, line):
        """Append a line to the report
        if the line exists it will merge it
        """
        if not type(ln) is int:
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

        if self.name.endswith(".rb") and self.totals.lines == self.totals.misses:
            # previous file was boil-the-ocean
            # OR previous file had END issue
            self._lines = other_file._lines

        elif (
            self.name.endswith(".rb")
            and other_file.totals.lines == other_file.totals.misses
        ):
            # skip boil-the-ocean files
            # OR skip 0% coverage files because END issue
            return False

        else:
            # set new lines object
            self._lines = [
                merge_line(before, after, joined)
                for before, after in zip_longest(self, other_file)
            ]

        self._totals = None
        return True

    @property
    def details(self):
        return self._details

    def _encode(self):
        return "%s\n%s" % (
            dumps(self.details, separators=(",", ":")),
            "\n".join(map(_dumps_not_none, self._lines)),
        )

    @property
    def totals(self):
        if not self._totals:
            self._totals = self._process_totals()
        return self._totals

    def _process_totals(self):
        """return dict of totals
        """
        cov, types, messages = [], [], []
        _cov, _types, _messages = cov.append, types.append, messages.append
        for ln, line in self.lines:
            _cov(line_type(line.coverage))
            _types(line.type)
            _messages(len(line.messages or []))

        hits = cov.count(0)
        misses = cov.count(1)
        partials = cov.count(2)
        lines = hits + misses + partials

        def sum_of_complexity(l):
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

        complexity = tuple(map(sum, zip(*map(sum_of_complexity, self.lines)))) or (0, 0)

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

    def apply_line_modifier(self, line_modifier):
        if line_modifier is None and self._line_modifier is None:
            return
        self._line_modifier = line_modifier
        self._totals = None

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

    def shift_lines_by_diff(self, diff, forward=True):
        try:
            remove = "-" if forward else "+"
            add = "+" if forward else "-"
            # loop through each segment
            for segment in diff["segments"]:
                # loop through each line
                pos = (int(segment["header"][2]) or 1) - 1
                for line in segment["lines"]:
                    if line[0] == remove:  # removed
                        self._lines.pop(pos)
                    elif line[0] == add:
                        pos += 1
                        self._lines.insert(pos, None)
                    else:
                        pos += 1
        except:
            # https://sentry.io/codecov/v4/issues/226391457/events/5041535451/
            pass


class Report(object):
    file_class = ReportFile

    def __init__(
        self,
        files=None,
        sessions=None,
        totals=None,
        chunks=None,
        diff_totals=None,
        yaml=None,
        flags=None,
        **kwargs
    ):
        # {"filename": [<line index in chunks :int>, <ReportTotals>]}
        self._files = files or {}
        for filename, file_summary in self._files.items():
            if not isinstance(file_summary, ReportFileSummary):
                self._files[filename] = ReportFileSummary(*file_summary)

        # {1: {...}}
        self.sessions = (
            dict(
                (int(sid), Session.parse_session(**session))
                for sid, session in sessions.items()
            )
            if sessions
            else {}
        )

        # ["<json>", ...]
        if isinstance(chunks, str):
            # came from archive
            chunks = chunks.split(END_OF_CHUNK)
        self._chunks = chunks or []

        # <ReportTotals>
        if isinstance(totals, ReportTotals):
            self._totals = totals

        elif totals:
            self._totals = ReportTotals(*migrate_totals(totals))

        else:
            self._totals = None

        self._path_filter = None
        self._line_modifier = None
        self._filter_cache = (None, None)
        self.diff_totals = diff_totals
        self.yaml = yaml  # ignored

    @property
    def network(self):
        if self._path_filter:
            for fname, data in self._files.items():
                file = self.get(fname)
                if file:
                    yield fname, make_network_file(file.totals)
        else:
            for fname, data in self._files.items():
                yield fname, make_network_file(
                    data.file_totals, data.session_totals, data.diff_totals
                )

    def __repr__(self):
        try:
            return "<%s files=%s>" % (
                self.__class__.__name__,
                len(getattr(self, "_files", [])),
            )
        except:
            return "<%s files=n/a>" % self.__class__.__name__

    @property
    def files(self):
        """returns a list of files in the report
        """
        path_filter = self._path_filter
        if path_filter:
            # return filtered list of filenames
            return [
                filename
                for filename, _ in self._files.items()
                if self._path_filter(filename)
            ]
        else:
            # return the fill list of filenames
            return list(self._files.keys())

    @property
    def flags(self):
        """returns dict(:name=<Flag>)
        """
        flags_dict = {}
        for sid, session in self.sessions.items():
            if session.flags:
                for flag in session.flags:
                    flags_dict[flag] = Flag(self, flag)
        return flags_dict

    def append(self, _file, joined=True):
        """adds or merged a file into the report
        """
        if _file is None:
            # skip empty adds
            return False

        elif not isinstance(_file, ReportFile):
            raise TypeError("expecting ReportFile got %s" % type(_file))

        elif len(_file) == 0:
            # dont append empty files
            return False

        assert _file.name, "file must have a name"
        session_n = len(self.sessions) - 1

        # check if file already exists
        index = self._files.get(_file.name)
        if index:
            # existing file
            # =============
            index.session_totals.append(copy(_file.totals))
            #  merge old report chunk
            cur_file = self[_file.name]
            # merge it
            cur_file.merge(_file, joined)
            # set totals
            index.file_totals = cur_file.totals
            # update chunk in report
            self._chunks[index.file_index] = cur_file
        else:
            # new file
            # ========
            session_totals = ([None] * session_n) + [_file.totals]

            # override totals
            if not joined:
                _file._totals = ReportTotals(0, _file.totals.lines)

            # add to network
            self._files[_file.name] = ReportFileSummary(
                len(self._chunks),  # chunk location
                _file.totals,  # Totals
                session_totals,  # Session Totals
                None,  # Diff Totals
            )

            # add file in chunks
            self._chunks.append(_file)

        self._totals = None

        return True

    def get(self, filename, _else=None, bind=False):
        """
        returns <ReportFile>
        if not found return _else

        :bind will replace the chunks and bind file changes to the report
        """
        if self._path_filter and not self._path_filter(filename):
            # filtered out of report
            return _else

        _file = self._files.get(filename)
        if _file is not None:
            if self._chunks:
                try:
                    lines = self._chunks[_file.file_index]
                except IndexError:
                    log.warning(
                        "File not found in chunk",
                        extra=dict(file_index=_file.file_index),
                        exc_info=True,
                    )
                    lines = None
            else:
                # may be tree_only request
                lines = None
            if isinstance(lines, ReportFile):
                lines.apply_line_modifier(self._line_modifier)
                return lines
            report_file = self.file_class(
                name=filename,
                totals=_file.file_totals,
                lines=lines,
                line_modifier=self._line_modifier,
            )
            if bind:
                self._chunks[_file[0]] = report_file

            return report_file

        return _else

    def ignore_lines(self, ignore_lines):
        """
        :ignore_lines {"path": {"lines": ["1"]}}
        only used during processing and does not effect the chunks inside this Report object
        """
        for path, data in ignore_lines.items():
            _file = self.get(path)
            if _file is not None:
                _file.ignore_lines(**data)

    def resolve_paths(self, paths):
        """
        :paths [(old_path, new_path), ...]
        """
        already_added_to_file = []
        paths_to_use = list(unique_everseen(paths))
        if len(paths_to_use) < len(paths):
            log.info("Paths being resolved were duplicated. Deduplicating")
        for old_path, new_path in paths_to_use:
            if old_path in self:
                if new_path in already_added_to_file:
                    del self[old_path]
                elif new_path is None:
                    del self[old_path]
                else:
                    already_added_to_file.append(new_path)
                    if old_path != new_path:
                        # rename and ignore lines
                        self.rename(old_path, new_path)

    def rename(self, old, new):
        # remvoe from list
        _file = self._files.pop(old)
        # add back with new name
        self._files[new] = _file
        # update name if it was a ReportFile
        chunk = self._chunks[_file.file_index]
        if isinstance(chunk, ReportFile):
            chunk.name = new
        return True

    def __getitem__(self, filename):
        _file = self.get(filename)
        if _file is None:
            raise IndexError("File at path %s not found in report" % filename)
        return _file

    def __delitem__(self, filename):
        # remove from report
        _file = self._files.pop(filename)
        # remove chunks
        self._chunks[_file.file_index] = None
        return True

    def get_folder_totals(self, path):
        """
        returns <ReportTotals> for files contained in a folder
        """
        path = path.strip("/") + "/"
        return sum_totals(
            (
                self[filename].totals
                for filename, _ in self._files.items()
                if filename.startswith(path)
            )
        )

    @property
    def totals(self):
        if not self._totals:
            # reprocess totals
            self._totals = self._process_totals()
        return self._totals

    def _process_totals(self):
        """Runs through the file network to aggregate totals
        returns <ReportTotals>
        """
        _path_filter = self._path_filter or bool
        _line_modifier = self._line_modifier

        def _iter_totals():
            for filename, data in self._files.items():
                if not _path_filter(filename):
                    continue
                elif _line_modifier or data.file_totals is None:
                    # need to rebuild the file because there are line filters
                    yield self.get(filename).totals
                else:
                    yield data.file_totals

        totals = agg_totals(_iter_totals())
        if self._filter_cache and self._filter_cache[1]:
            flags = set(self._filter_cache[1])
            totals.sessions = len(
                [
                    1
                    for _, session in self.sessions.items()
                    if set(session.flags or []) & flags
                ]
            )
        else:
            totals.sessions = len(self.sessions)

        return ReportTotals(*tuple(totals))

    @property
    def manifest(self):
        """returns a list of files in the report
        """
        if self._path_filter:
            return list(filter(self._path_filter, list(self._files)))

        else:
            return list(self._files)

    def next_session_number(self):
        start_number = len(self.sessions)
        while start_number in self.sessions or str(start_number) in self.sessions:
            start_number += 1
        return start_number

    def add_session(self, session):
        sessionid = self.next_session_number()
        self.sessions[sessionid] = session
        if self._totals:
            # add session to totals
            self._totals = dataclasses.replace(self._totals, sessions=sessionid + 1)
        return sessionid, session

    def __iter__(self):
        """Iter through all the files
        yielding <ReportFile>
        """
        for filename, _file in self._files.items():
            if self._path_filter and not self._path_filter(filename):
                # filtered out
                continue
            if self._chunks:
                report = self._chunks[_file.file_index]
            else:
                report = None
            if isinstance(report, ReportFile):
                yield report
            else:
                yield self.file_class(
                    name=filename,
                    totals=_file.file_totals,
                    session_totals=_file.session_totals
                    if _file.session_totals
                    else None,
                    lines=report,
                    line_modifier=self._line_modifier,
                )

    def __contains__(self, filename):
        return filename in self._files

    def merge(self, new_report, joined=True):
        """combine report data from another
        """
        if new_report is None:
            return

        elif not isinstance(new_report, Report):
            raise TypeError("expecting type Report got %s" % type(new_report))

        elif new_report.is_empty():
            return

        # merge files
        for _file in new_report:
            if _file.name:
                self.append(_file, joined)

        self._totals = self._process_totals()

    def is_empty(self):
        """returns boolean if the report has no content
        """
        if self._path_filter:
            return len(list(filter(self._path_filter, list(self._files.keys())))) == 0
        else:
            return len(self._files) == 0

    def __bool__(self):
        return self.is_empty() is False

    def to_archive(self):
        # TODO: confirm removing encoding here is fine
        return END_OF_CHUNK.join(map(_encode_chunk, self._chunks))

    def to_database(self):
        """returns (totals, report) to be stored in database
        """
        totals = dict(zip(TOTALS_MAP, self.totals))
        totals["diff"] = self.diff_totals
        return (
            totals,
            dumps({"files": self._files, "sessions": self.sessions}, cls=ReportEncoder),
        )

    def update_sessions(self, **data):
        pass

    def flare(self, changes=None, color=None):
        if changes is not None:
            """
            if changes are provided we produce a new network
            only pass totals if they change
            """
            # <dict path: totals if not new else None>
            changed_coverages = dict(
                (
                    (
                        individual_change.path,
                        individual_change.totals.coverage
                        if not individual_change.new and individual_change.totals
                        else None,
                    )
                    for individual_change in changes
                )
            )
            # <dict path: stripeed if not in_diff>
            classes = dict(
                ((_Change.path, "s") for _Change in changes if not _Change.in_diff)
            )

            def _network():
                for name, _NetworkFile in self.network:
                    changed_coverage = changed_coverages.get(name)
                    if changed_coverage:
                        # changed file
                        yield name, ReportTotals(
                            lines=_NetworkFile.totals.lines,
                            coverage=float(changed_coverage),
                        )
                    else:
                        diff = _NetworkFile.diff_totals
                        if diff and diff.lines > 0:  # lines > 0
                            # diff file
                            yield name, ReportTotals(
                                lines=_NetworkFile.totals.lines,
                                coverage=-1
                                if float(diff.coverage)
                                < float(_NetworkFile.totals.coverage)
                                else 1,
                            )

                        else:
                            # unchanged file
                            yield name, ReportTotals(lines=_NetworkFile.totals.lines)

            network = _network()

            def color(cov):
                return (
                    "purple"
                    if cov is None
                    else "#e1e1e1"
                    if cov == 0
                    else "green"
                    if cov > 0
                    else "red"
                )

        else:
            network = (
                (path, _NetworkFile.totals) for path, _NetworkFile in self.network
            )
            classes = {}
            # [TODO] [v4.4.0] remove yaml from args, use below
            # color = self.yaml.get(('coverage', 'range'))

        return report_to_flare(network, color, classes)

    def reset(self):
        # remove my totals
        self._totals = None
        self._path_filter = None
        self._line_modifier = None
        self._filter_cache = None

    def filter(self, paths=None, flags=None):
        """Usage: with report.filter(repository, paths, flags) as report: ...
        """
        if self._filter_cache == (paths or None, flags or None):
            # same same
            return self

        self._filter_cache = (paths, flags)
        self.reset()

        if paths or flags:
            # reset all totals
            if paths:
                if not isinstance(paths, (list, set, tuple)):
                    raise TypeError(
                        "expecting list for argument paths got %s" % type(paths)
                    )

                def _pf(filename):
                    return match(paths, filename)

                self._path_filter = _pf

            # flags: filter them out
            if flags:
                if not isinstance(flags, (list, set, tuple)):
                    flags = [flags]

                # get all session ids that have this falg
                sessions = set(
                    [
                        int(sid)
                        for sid, session in self.sessions.items()
                        if match_any(flags, session.flags)
                    ]
                )

                # the line has data from this session
                def adjust_line(line):
                    new_sessions = [
                        LineSession(*s) if not isinstance(s, LineSession) else s
                        for s in (line.sessions or [])
                        if int(s.id) in sessions
                    ]
                    # check if line is applicable
                    if not new_sessions:
                        return False
                    return ReportLine(
                        coverage=get_coverage_from_sessions(new_sessions),
                        complexity=get_complexity_from_sessions(new_sessions),
                        type=line.type,
                        sessions=new_sessions,
                        messages=line.messages,
                    )

                self._line_modifier = adjust_line

        return self

    def __enter__(self):
        """see self.filter
        Usage: with report.filter() as report: ...
        """
        return self

    def __exit__(self, *args):
        """remove filtering
        """
        # removes all filters
        self.reset()

    def does_diff_adjust_tracked_lines(self, diff, future_report, future_diff):
        """
        Returns <boolean> if the diff touches tracked lines

        master . A . C
        pull          \ . . B

        :diff = <diff> A...C
        :future_report = <report> B
        :future_diff = <diff> C...B

        future_report is necessary because it is used to determin if
        lines added in the diff are tracked by codecov
        """
        if diff and diff.get("files"):
            for path, data in diff["files"].items():
                future_state = walk(future_diff, ("files", path, "type"))
                if data["type"] == "deleted" and path in self:  # deleted  # and tracked
                    # found a file that was tracked and deleted
                    return True

                elif (
                    data["type"] == "new"
                    and future_state != "deleted"  # newly tracked
                    and path  # not deleted in future
                    in future_report  # found in future
                ):
                    # newly tracked file
                    return True

                elif data["type"] == "modified":
                    in_past = path in self
                    in_future = future_state != "deleted" and path in future_report
                    if in_past and in_future:

                        # get the future version
                        future_file = future_report.get(path, bind=False)
                        # if modified
                        if future_state == "modified":
                            # shift the lines to "guess" what C was
                            future_file.shift_lines_by_diff(
                                future_diff["files"][path], forward=False
                            )

                        if self.get(path).does_diff_adjust_tracked_lines(
                            data, future_file
                        ):
                            # lines changed
                            return True

                    elif in_past and not in_future:
                        # missing in future
                        return True

                    elif not in_past and in_future:
                        # missing in pats
                        return True

        return False

    def shift_lines_by_diff(self, diff, forward=True):
        """
        [volitile] will permanently adjust repot report

        Takes a <diff> and offsets the line based on additions and removals
        """
        if diff and diff.get("files"):
            for path, data in diff["files"].items():
                if data["type"] == "modified" and path in self:
                    _file = self.get(path)
                    _file.shift_lines_by_diff(data, forward=forward)
                    chunk_loc = self._files[path][0]
                    # update chunks with file updates
                    self._chunks[chunk_loc] = _file
                    # clear out totals
                    self._files[path] = [chunk_loc, None, None, None]

    def apply_diff(self, diff, _save=True):
        """
        Add coverage details to the diff at ['coverage'] = <ReportTotals>
        returns <ReportTotals>
        """
        if diff and diff.get("files"):
            totals = []
            for path, data in diff["files"].items():
                if data["type"] in ("modified", "new"):
                    _file = self.get(path)
                    if _file:
                        fg = _file.get
                        lines = []
                        le = lines.extend
                        # add all new lines data to a new file to get totals
                        [
                            le(
                                [
                                    fg(i)
                                    for i, line in enumerate(
                                        [l for l in segment["lines"] if l[0] != "-"],
                                        start=int(segment["header"][2]) or 1,
                                    )
                                    if line[0] == "+"
                                ]
                            )
                            for segment in data["segments"]
                        ]

                        file_totals = ReportFile(
                            name=None, totals=None, lines=lines
                        ).totals
                        totals.append(file_totals)
                        if _save:
                            data["totals"] = file_totals
                            # store in network
                            network_file = self._files[path]
                            if file_totals.lines == 0:
                                # no lines touched
                                file_totals = dataclasses.replace(
                                    file_totals,
                                    coverage=None,
                                    complexity=None,
                                    complexity_total=None,
                                )
                            network_file.diff_totals = file_totals

            totals = sum_totals(totals)

            if totals.lines == 0:
                totals = dataclasses.replace(
                    totals, coverage=None, complexity=None, complexity_total=None
                )

            if _save and totals.files:
                diff["totals"] = totals
                self.diff_totals = totals

            return totals

    def has_flag(self, flag_name):
        """
        Returns boolean: if the flag is found
        """
        for sid, data in self.sessions.items():
            if flag_name in (data.flags or []):
                return True
        return False

    def assume_flags(self, flags, prev_report, name=None):
        with prev_report.filter(flags=flags) as filtered:
            # add the "assumed session"
            self.add_session(
                Session(flags=flags, totals=filtered.totals, name=name or "Assumed")
            )
            # merge the results
            self.merge(filtered)


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
            return lambda l: str(l) > eof or l in lines
        # This means the eof as a number: the last line of the file and
        # anything after that should be ignored
        return lambda l: l > eof or l in lines
    else:
        return lambda l: l in lines


def _dumps_not_none(value):
    if isinstance(value, list):
        return dumps(_rstrip_none(list(value)), cls=ReportEncoder)
    if isinstance(value, ReportLine):
        return dumps(_rstrip_none(list(value.astuple())), cls=ReportEncoder)
    return value if value and value != "null" else ""


def _rstrip_none(lst):
    while lst[-1] is None:
        lst.pop(-1)
    return lst


class EnhancedJSONEncoder(JSONEncoder):
    def default(self, o):
        if dataclasses.is_dataclass(o):
            return o.astuple()
        return super().default(o)


def _encode_chunk(chunk):
    if chunk is None:
        return "null"
    elif isinstance(chunk, ReportFile):
        return chunk._encode()
    elif isinstance(chunk, (list, dict)):
        return dumps(chunk, separators=(",", ":"), cls=EnhancedJSONEncoder)
    else:
        return chunk
