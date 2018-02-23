from src.utils.merge import *
from json import loads, dumps
from itertools import izip_longest
from src.utils.tuples import *
from src.helpers.ratio import ratio
from src.utils.ReportEncoder import ReportEncoder


class ReportFile(object):
    __slot__ = ('name', '_details', '_lines',
                '_line_modifier', '_ignore',
                '_totals', '_session_totals')

    def __init__(self, name, totals=None,
                 session_totals=None,
                 lines=None, line_modifier=None,
                 ignore=None):
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
                self._details = loads(lines.pop(0) or 'null')
                self._lines = lines
        else:
            self._details = {}
            self._lines = []

        # <line_modifier callable>
        self._line_modifier = line_modifier
        self._ignore = ignore_to_func(ignore) if ignore else None

        if line_modifier:
            self._totals = None  # need to reprocess these
        else:
            # totals = <ReportTotals []>
            self._totals = ReportTotals(*totals) if totals else None

        self._session_totals = session_totals

    def __repr__(self):
        try:
            return '<%s name=%s lines=%s>' % (self.__class__.__name__, self.name, len(self))
        except:
            return '<%s name=%s lines=n/a>' % (self.__class__.__name__, self.name)

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
                line[2] = [LineSession(*tuple(session)) for session in line[2] if session]
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
                    self._lines[ln-1] = None
        if eof:
            self._lines = self._lines[:eof]
        self._totals = None

    def __getitem__(self, ln):
        """Return a single line or None
        """
        if ln == 'totals':
            return self.totals
        if not type(ln) is int:
            raise TypeError('expecting type int got %s' % type(ln))
        elif ln < 1:
            raise ValueError('Line number must be greater then 0. Got %s' % ln)
        _line = self.get(ln)
        if not _line:
            raise IndexError('Line #%s not found in report' % ln)
        return _line

    def __setitem__(self, ln, line):
        """Append line to file, without merging if previously set
        """
        if not type(ln) is int:
            raise TypeError('expecting type int got %s' % type(ln))
        elif not isinstance(line, ReportLine):
            raise TypeError('expecting type ReportLine got %s' % type(line))
        elif ln < 1:
            raise ValueError('Line number must be greater then 0. Got %s' % ln)
        elif self._ignore and self._ignore(ln):
            return

        length = len(self._lines)
        if length <= ln:
            self._lines.extend([EMPTY] * (ln - length))

        self._lines[ln-1] = line
        return

    def __len__(self):
        """Returns count(number of lines with coverage data)
        """
        return len(filter(None, self._lines))

    @property
    def eof(self):
        """Returns count(number of lines)
        """
        return len(self._lines) + 1

    def __getslice__(self, start, stop):
        """Retrns a stream of lines between two indexes

        slice = report[5:25]


        for ln, line in report[5:25]:
            ...

        slice = report[5:25]
        assert slice is gernerator.
        list(slice) == [(1, Line), (2, Line)]


        """
        func = self._line_modifier
        for ln, line in enumerate(self._lines[start-1:stop-1], start=start):
            if line:
                line = self._line(line)
                if func:
                    line = func(line)
                    if not line:
                        continue
                yield ln, line

    def __contains__(self, ln):
        if not type(ln) is int:
            raise TypeError('expecting type int got %s' % type(ln))
        try:
            return self.get(ln) is not None
        except IndexError:
            return False

    def __nonzero__(self):
        return self.totals.lines > 0

    def get(self, ln, raises_index_error=False):
        if not type(ln) is int:
            raise TypeError('expecting type int got %s' % type(ln))
        elif ln < 1:
            raise ValueError('Line number must be greater then 0. Got %s' % ln)

        try:
            line = self._lines[ln-1]

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
            raise TypeError('expecting type int got %s' % type(ln))
        elif not isinstance(line, ReportLine):
            raise TypeError('expecting type ReportLine got %s' % type(line))
        elif ln < 1:
            raise ValueError('Line number must be greater then 0. Got %s' % ln)
        elif self._ignore and self._ignore(ln):
            return False

        length = len(self._lines)
        if length <= ln:
            self._lines.extend([EMPTY] * (ln - length))
        _line = self.get(ln)
        if _line:
            self._lines[ln-1] = merge_line(_line, line)
        else:
            self._lines[ln-1] = line
        return True

    def merge(self, other_file, joined=True):
        """merges another report chunk
        returning the <dict totals>
        It's quicker to run the totals during processing
        """
        if other_file is None:
            return

        elif not isinstance(other_file, ReportFile):
            raise TypeError('expecting type ReportFile got %s' % type(other_file))

        if (
                self.name.endswith('.rb') and
                self.totals.lines == self.totals.misses
        ):
            # previous file was boil-the-ocean
            # OR previous file had END issue
            self._lines = other_file._lines

        elif (
                self.name.endswith('.rb') and
                other_file.totals.lines == other_file.totals.misses
        ):
            # skip boil-the-ocean files
            # OR skip 0% coverage files because END issue
            return False

        else:
            # set new lines object
            self._lines = [merge_line(before, after, joined)
                           for before, after
                           in izip_longest(self, other_file)]

        self._totals = None
        return True

    def _encode(self):
        return '%s\n%s' % (dumps(self._details, separators=(',', ':')),
                           '\n'.join(map(dumps_not_none, self._lines)))

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
            c = l[1][4]
            if not c:
                # no coverage data provided
                return (0, 0)
            elif type(c) is int:
                # coverage is of type int
                return (c, 0)
            else:
                # coverage is ratio
                return c

        complexity = tuple(map(sum,
                               zip(*map(sum_of_complexity,
                                        self.lines)))) or (0, 0)

        return ReportTotals(files=0,
                            lines=lines,
                            hits=hits,
                            misses=misses,
                            partials=partials,
                            coverage=ratio(hits, lines) if lines else None,
                            branches=types.count('b'),
                            methods=types.count('m'),
                            messages=sum(messages),
                            sessions=0,
                            complexity=complexity[0],
                            complexity_total=complexity[1])

    def apply_line_modifier(self, line_modifier):
        if line_modifier is None and self._line_modifier is None:
            return
        self._line_modifier = line_modifier
        self._totals = None

    def does_diff_adjust_tracked_lines(self, diff, future_file):
        for segment in diff['segments']:
            # loop through each line
            pos = (int(segment['header'][2]) or 1)
            for line in segment['lines']:
                if line[0] == '-':
                    if pos in self:
                        # tracked line removed
                        return True

                elif line[0] == '+':
                    if pos in future_file:
                        # tracked line added
                        return True
                    pos += 1
                else:
                    pos += 1
        return False

    def shift_lines_by_diff(self, diff, forward=True):
        try:
            remove = '-' if forward else '+'
            add = '+' if forward else '-'
            # loop through each segment
            for segment in diff['segments']:
                # loop through each line
                pos = (int(segment['header'][2]) or 1) - 1
                for line in segment['lines']:
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


def ignore_to_func(ignore):
    eof = ignore.get('eof')
    lines = ignore.get('lines') or []
    if eof:
        return lambda l: l > eof or l in lines
    else:
        return lambda l: l in lines

def dumps_not_none(value):
    if isinstance(value, (list, ReportLine)):
        return dumps(_rstrip_none(list(value)),
                     cls=ReportEncoder)
    return value if value and value != 'null' else ''


def _rstrip_none(lst):
    while lst[-1] is None:
        lst.pop(-1)
    return lst
