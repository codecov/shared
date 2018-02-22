from copy import copy
import types as ObjTypes
from json import JSONEncoder
from json import loads, dumps
from operator import itemgetter
from collections import defaultdict
from itertools import chain, groupby, izip_longest, izip, imap, starmap

from src.utils.tuples import *
from utils.Yaml import Yaml
from helpers.flag import Flag
from helpers.ratio import ratio
from helpers.sessions import Session
from helpers.flare import report_to_flare
from helpers.migrate import migrate_totals
from helpers.match import match, match_any


def combine_partials(partials):
    """
        [(INCLUSIVE, EXCLUSICE, HITS), ...]
        | . . . . . |
     in:    0+         (2, None, 0)
     in:  1   1        (1, 3, 1)
    out:  1 1 1 0 0
    out:  1   1 0+     (1, 3, 1), (4, None, 0)
    """
    # only 1 partial: return same
    if len(partials) == 1:
        return partials

    columns = defaultdict(list)
    # fill in the partials WITH end values: (_, X, _)
    [[columns[c].append(cov) for c in xrange(sc or 0, ec)]
     for (sc, ec, cov) in partials
     if ec is not None]

    # get the last column number (+1 for exclusiveness)
    lc = (max(columns.keys()) if columns else max([sc or 0 for (sc, ec, cov) in partials])) + 1
    # hits for (lc, None, eol)
    eol = []

    # fill in the partials WITHOUT end values: (_, None, _)
    [([columns[c].append(cov) for c in xrange(sc or 0, lc)], eol.append(cov))
     for (sc, ec, cov) in partials
     if ec is None]

    columns = [(c, merge_all(cov)) for c, cov in columns.iteritems()]

    # sum all the line hits && sort and group lines based on hits
    columns = groupby(sorted(columns), lambda (c, h): h)

    results = []
    for cov, cols in columns:
        # unpack iter
        cols = list(cols)
        # sc from first column
        # ec from last (or +1 if singular)
        results.append([cols[0][0], (cols[-1] if cols else cols[0])[0] + 1, cov])

    # remove duds
    if results:
        fp = results[0]
        if fp[0] == 0 and fp[1] == 1:
            results.pop(0)
            if not results:
                return [[0, None, fp[2]]]

        # if there is eol data
        if eol:
            eol = merge_all(eol)
            # if the last partial ec == lc && same hits
            lr = results[-1]
            if lr[1] == lc and lr[2] == eol:
                # then replace the last partial with no end
                results[-1] = [lr[0], None, eol]
            else:
                # else append a new eol partial
                results.append([lc, None, eol])

    return results or None


def merge_all(coverages, missing_branches=None):
    if len(coverages) == 1:
        return coverages[0]

    cov = coverages[0]
    for _ in coverages[1:]:
        cov = merge_coverage(cov, _, missing_branches)
    return cov


def branch_type(b):
    """
    0 = hit
    1 = miss
    2 = partial
    """
    b1, b2 = tuple(b.split('/', 1))
    return 0 if b1 == b2 else 1 if b1 == '0' else 2


def line_type(line):
    """
    -1 = skipped (had coverage data, but fixed out)
    0 = hit
    1 = miss
    2 = partial
    None = ignore (because it has messages or something)
    """
    return 2 if line is True else \
        branch_type(line) if type(line) in (str, unicode) else \
        -1 if line == -1 else \
        None if line is False else \
        0 if line else \
        1 if line is not None else None


def zfill(lst, index, value):
    ll = len(lst)
    if len(lst) <= index:
        lst.extend([None] * (index - ll + 1))
    lst[index] = value
    return lst


def list_to_dict(lines):
    """
    in:  [None, 1] || {"1": 1}
    out: {"1": 1}
    """
    if type(lines) is list:
        if len(lines) > 1:
            return dict([(ln, cov) for ln, cov in enumerate(lines[1:], start=1) if cov is not None])
        else:
            return {}
    else:
        return lines or {}


def merge_branch(b1, b2):
    if b1 == b2:  # 1/2 == 1/2
        return b1
    elif b1 == -1 or b2 == -1:
        return -1
    elif type(b1) in (int, long) and b1 > 0:
        return b1
    elif type(b2) in (int, long) and b2 > 0:
        return b2
    elif b1 in (0, None, True):
        return b2
    elif b2 in (0, None, True):
        return b1
    elif type(b1) is list:
        return b1
    elif type(b2) is list:
        return b2
    br1, br2 = tuple(b1.split('/', 1))
    if br1 == br2:  # equal 1/1
        return b1
    br3, br4 = tuple(b2.split('/', 1))
    if br3 == br4:  # equal 1/1
        return b2
    # return the greatest found
    return "%s/%s" % (br1 if int(br1) > int(br3) else br3,
                      br2 if int(br2) > int(br3) else br4)


def _ifg(s, e, c):
    """
    s=start, e=end, c=coverage
    Insures the end is larger then the start.
    """
    return [s, e if e > s else s+1, c]


def partials_to_line(partials):
    """
        | . . . . . |
    in:   1 1 1 0 0
    out: 1/2
        | . . . . . |
    in:   1 0 1 0 0
    out: 2/4
    """
    ln = len(partials)
    if ln == 1:
        return partials[0][2]
    return '%s/%s' % (sum([1 for (sc, ec, hits) in partials if hits > 0]), ln)


def get_coverage_from_sessions(sessions):
    return merge_all([s[1] for s in sessions], merge_missed_branches(sessions))


def get_complexity_from_sessions(sessions):
    _type = type(sessions[0][4])
    if _type is int:
        return max([(s[4] or 0) for s in sessions])
    elif _type in (tuple, list):
        return (max([(s[4] or (0, 0))[0] for s in sessions]),
                max([(s[4] or (0, 0))[1] for s in sessions]))


def merge_partial_line(p1, p2):
    if not p1 or not p2:
        return p1 or p2

    np = p1 + p2
    if len(np) == 1:
        # one result already
        return np

    fl = defaultdict(list)
    [[fl[x].append(_c) for x in xrange(_s or 0, _e + 1)] for _s, _e, _c in np if _e is not None]
    ks = fl.keys()
    mx = max(ks)+1 if ks else 0
    # appends coverage on each column when [X, None, C]
    [[fl[x].append(_c) for x in xrange(_s or 0, mx)] for _s, _e, _c in np if _e is None]
    ks = fl.keys()
    # fl = {1: [1], 2: [1], 4: [0], 3: [1], 5: [0], 7: [0], 8: [0]}
    pp = []
    append = pp.append
    for cov, group in groupby(sorted([(cl, max(cv)) for cl, cv in fl.items()]), lambda c: c[1]):
        group = list(group)
        append(_ifg(group[0][0], group[-1][0], cov))

    # never ends
    if [[max(ks), None, _c] for _s, _e, _c in np if _e is None]:
        pp[-1][1] = None

    return pp


_types = {
    ObjTypes.StringType: ObjTypes.StringType,
    ObjTypes.UnicodeType: ObjTypes.StringType,
    ObjTypes.LongType: ObjTypes.FloatType,
    ObjTypes.IntType: ObjTypes.FloatType,
    ObjTypes.FloatType: ObjTypes.FloatType,
    ObjTypes.ListType: ObjTypes.ListType,
    ObjTypes.BooleanType: ObjTypes.BooleanType
}.get


def merge_coverage(l1, l2, branches_missing=True):
    if l1 is None or l2 is None:
        return l1 if l1 is not None else l2

    elif l1 == -1 or l2 == -1:
        # ignored line
        return -1

    l1t = _types(type(l1))
    l2t = _types(type(l2))

    if l1t is float and l2t is float:
        return l1 if l1 >= l2 else l2

    elif l1t is str or l2t is str:
        if l1t is float:
            # using or here because if l1 is 0 return l2
            # this will trigger 100% if l1 is > 0
            branches_missing = [] if l1 else False
            l1 = l2

        elif l2t is float:
            branches_missing = [] if l2 else False

        if branches_missing == []:
            # all branches were hit, no need to merge them
            l1 = l1.split('/')[-1]
            return '%s/%s' % (l1, l1)

        elif type(branches_missing) is list:
            # we know how many are missing
            target = int(l1.split('/')[-1])
            bf = (target - len(branches_missing))
            return '%s/%s' % (bf if bf > 0 else 0, target)

        return merge_branch(l1, l2)

    elif l1t is list and l2t is list:
        return merge_partial_line(l1, l2)

    elif l1t is bool or l2t is bool:
        return (l2 or l1) if l1t is bool else (l1 or l2)

    return merge_coverage(partials_to_line(l1) if l1t is list else l1,
                          partials_to_line(l2) if l2t is list else l2)


def sum_totals(totals):
    totals = filter(None, totals)
    if not totals:
        return ReportTotals()

    sessions = totals[0][9]
    lines = sum(map(itemgetter(1), totals))
    hits = sum(map(itemgetter(2), totals))
    return ReportTotals(files=len(totals),
                        lines=lines,
                        hits=hits,
                        misses=sum(map(itemgetter(3), totals)),
                        partials=sum(map(itemgetter(4), totals)),
                        branches=sum(map(itemgetter(6), totals)),
                        methods=sum(map(itemgetter(7), totals)),
                        messages=sum(map(itemgetter(8), totals)),
                        coverage=ratio(hits, lines),
                        sessions=sessions,
                        complexity=sum(map(itemgetter(10), totals)),
                        complexity_total=sum(map(itemgetter(11), totals)))


def merge_missed_branches(sessions):
    """returns
    None: if there is no branch data provided
    []: list of missing branches
    """
    if sessions:
        if [1 for s in sessions if s.branches is not None] == []:
            # no branch data provided in any session
            return None

        # missing branches or fulfilled if type=hit else not applicable
        mb = [s.branches if s.branches is not None else ([] if line_type(s.coverage) == 0 else None)
              for s in sessions
              if s]

        # one of the sessions collected all the branches
        if [] in mb:
            return []

        else:
            # missing branches, remove "None"s
            mb = filter(None, mb)
            # # no branch data provided
            # if not mb:
            #     return []

            # we only have one missing branches data
            if len(mb) == 1:
                return mb[0]

            else:
                # combine the branches
                mb = map(set, mb)
                m1 = mb.pop(0)
                for m in mb:
                    m1 = m1 & m
                return list(m1)


def merge_line(l1, l2, joined=True):
    if not l1 or not l2:
        return l1 or l2

    # merge sessions
    sessions = merge_sessions(list(l1.sessions or []), list(l2.sessions or []))

    return ReportLine(type=l1.type or l2.type,
                      coverage=get_coverage_from_sessions(sessions) if joined else l1.coverage,
                      complexity=get_complexity_from_sessions(sessions) if joined else l1.complexity,
                      sessions=sessions,
                      messages=merge_messages(l1.messages, l2.messages))


def merge_messages(m1, m2):
    pass


def merge_line_session(s1, s2):
    s1b = s1.branches
    s2b = s2.branches
    if s1b is None and s2b is None:
        # all are None, so return None
        mb = None
    elif s1b is None:
        if line_type(s1.coverage) == 0:
            # s1 was a hit, so we have no more branches to get
            mb = []
        else:
            mb = s2b
    elif s2b is None:
        if line_type(s2.coverage) == 0:
            # s2 was a hit, so we have no more branches to get
            mb = []
        else:
            mb = s1b
    else:
        mb = list(set(s1b or []) & set(s2b or []))

    s1p = s1.partials
    s2p = s2.partials
    partials = None
    if s1p or s2p:
        if s1p is None or s2p is None:
            partials = s1p or s2p
        else:
            # list + list
            partials = sorted(s1p + s2p, key=lambda p: p[0])

    return LineSession(s1.id, merge_coverage(s1.coverage, s2.coverage, mb), mb, partials)


def merge_sessions(s1, s2):
    """Merges two lists of different sessions into one
    """
    if not s1 or not s2:
        return s1 or s2

    s1k = set([s[0] for s in s1])
    s2k = set([s[0] for s in s2])
    same = s1k & s2k
    if same:
        s1 = dict([(s[0], s) for s in s1])
        s2 = dict([(s[0], s) for s in s2])

        # merge existing
        for s in same:
            s1[s] = merge_line_session(LineSession(*s1[s]),
                                       LineSession(*s2.pop(s)))

        # add remaining new sessions
        s1 = s1.values() + s2.values()

    else:
        s1.extend(s2)

    return list(starmap(LineSession, s1))


def is_branch(cov):
    return 1 if type(cov) in (str, unicode, bool) else 0


def branch_value(br):
    return 2 if type(br) in (bool, int, float, long) else int(br.split('/')[-1])


def _sum(array):
    if array:
        if not isinstance(array[0], (type(None), basestring)):
            try:
                return sum(array)
            except:
                # https://sentry.io/codecov/v4/issues/159966549/
                return sum(map(lambda a: a if type(a) is int else 0, array))
    return None


def agg_totals(totals):
    totals = filter(None, totals)
    n_files = len(totals)
    totals = list(imap(_sum, izip(*totals)))
    if not totals:
        return list(ReportTotals.__new__.__defaults__)
    totals[0] = n_files
    totals[5] = ratio(totals[2], totals[1])
    return totals


def make_network_file(totals, sessions=None, diff=None):
    return NetworkFile(
        ReportTotals(*totals) if totals else ReportTotals(),
        [ReportTotals(*session) if session else None for session in sessions] if sessions else None,
        ReportTotals(*diff) if diff else None
    )


def _rstrip_none(lst):
    while lst[-1] is None:
        lst.pop(-1)
    return lst


def dumps_not_none(value):
    if isinstance(value, (list, ReportLine)):
        return dumps(_rstrip_none(list(value)),
                     cls=ReportEncoder)
    return value if value and value != 'null' else ''


def ignore_to_func(ignore):
    eof = ignore.get('eof')
    lines = ignore.get('lines') or []
    if eof:
        return lambda l: l > eof or l in lines
    else:
        return lambda l: l in lines


class ReportEncoder(JSONEncoder):
    separators = (',', ':')

    def default(self, obj):
        if isinstance(obj, ReportTotals):
            # reduce totals
            obj = list(obj)
            while obj and obj[-1] in ('0', 0):
                obj.pop()
            return obj
        elif isinstance(obj, (Session, ReportFile)):
            return obj._encode()
        elif isinstance(obj, ObjTypes.GeneratorType):
            obj = list(obj)
        # let the base class default method raise the typeerror
        return JSONEncoder.default(self, obj)


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


def _encode_chunk(chunk):
    if chunk is None:
        return 'null'
    elif isinstance(chunk, ReportFile):
        return chunk._encode()
    elif isinstance(chunk, (list, dict)):
        return dumps(chunk, separators=(',', ':'))
    else:
        return chunk


END_OF_CHUNK = '\n<<<<< end_of_chunk >>>>>\n'

# files={
#     "filename": [chunk_i, ....]
# }
# chunks="""
# null
# [1,...]  # data at line 1
# [1,...]  # data at line 2
#
# [1,...]  # data at line 4
# <<<<< end_of_chunk >>>>>
# null
# [1,...]  # data at line 1
# [1,...]  # data at line 2
#
# [1,...]  # data at line 4
#
# """
#
# files['filename'][0] => 1
#
# chunks[1] => """null
# [1,...]  # data at line 1
# [1,...]  # data at line 2
#
# [1,...]  # data at line 4
# """
#
# chunks[1].splitlines()[4]  = json.loads("[1,...]  # data at line 4")

class Report(object):
    file_class = ReportFile

    def __init__(self, files=None, sessions=None,
                 totals=None, chunks=None, diff_totals=None,
                 yaml=None, flags=None, **kwargs):
        # {"filename": [<line index in chunks :int>, <ReportTotals>]}
        self._files = files or {}

        # {1: {...}}
        self.sessions = dict((sid, Session(**session))
                             for sid, session
                             in sessions.iteritems()) if sessions else {}

        # ["<json>", ...]
        if isinstance(chunks, basestring):
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
            for fname, data in self._files.iteritems():
                file = self.get(fname)
                if file:
                    yield fname, make_network_file(
                        file.totals
                    )
        else:
            for fname, data in self._files.iteritems():
                yield fname, make_network_file(*data[1:])

    def __repr__(self):
        try:
            return '<%s files=%s>' % (
                self.__class__.__name__,
                len(getattr(self, '_files', [])))
        except:
            return '<%s files=n/a>' % self.__class__.__name__

    @property
    def files(self):
        """returns a list of files in the report
        """
        path_filter = self._path_filter
        if path_filter:
            # return filtered list of filenames
            return [filename
                    for filename, _ in self._files.iteritems()
                    if self._path_filter(filename)]
        else:
            # return the fill list of filenames
            return self._files.keys()

    @property
    def flags(self):
        """returns dict(:name=<Flag>)
        """
        return {flag: Flag(self, flag)
                for flag
                in set(chain(*((session.flags or [])
                               for sid, session
                               in self.sessions.iteritems())))}

    def append(self, _file, joined=True):
        """adds or merged a file into the report
        """
        if _file is None:
            # skip empty adds
            return False

        elif not isinstance(_file, ReportFile):
            raise TypeError('expecting ReportFile got %s' % type(_file))

        elif len(_file) == 0:
            # dont append empty files
            return False

        assert _file.name, 'file nust have a name'

        session_n = len(self.sessions) - 1

        # check if file already exists
        index = self._files.get(_file.name)
        if index:
            # existing file
            # =============
            # add session totals
            if len(index) < 3:
                # [TEMP] this may be temporary, as old report dont have sessoin totals yet
                index.append([])
            index[2].append(copy(_file.totals))
            #  merge old report chunk
            cur_file = self[_file.name]
            # merge it
            cur_file.merge(_file, joined)
            # set totals
            index[1] = cur_file.totals
            # update chunk in report
            self._chunks[index[0]] = cur_file
        else:
            # new file
            # ========
            session_totals = ([None] * session_n) + [_file.totals]

            # override totals
            if not joined:
                _file._totals = ReportTotals(0, _file.totals.lines)

            # add to network
            self._files[_file.name] = [
                len(self._chunks),       # chunk location
                _file.totals,            # Totals
                session_totals,          # Session Totals
                None                     # Diff Totals
            ]

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
                    lines = self._chunks[_file[0]]
                except:
                    lines = None
                    print '[DEBUG] file not found in chunk', _file[0]
            else:
                # may be tree_only request
                lines = None
            if isinstance(lines, ReportFile):
                lines.apply_line_modifier(self._line_modifier)
                return lines
            report_file = self.file_class(name=filename,
                                          totals=_file[1],
                                          lines=lines,
                                          line_modifier=self._line_modifier)
            if bind:
                self._chunks[_file[0]] = report_file

            return report_file

        return _else

    def ignore_lines(self, ignore_lines):
        """
        :ignore_lines {"path": {"lines": ["1"]}}
        """
        for path, data in ignore_lines.iteritems():
            _file = self.get(path)
            if _file is not None:
                _file.ignore_lines(**data)

    def resolve_paths(self, paths):
        """
        :paths [(old_path, new_path), ...]
        """
        already_added_to_file = []
        for old_path, new_path in paths:
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
        chunk = self._chunks[_file[0]]
        if isinstance(chunk, ReportFile):
            chunk.name = new
        return True

    def __getitem__(self, filename):
        _file = self.get(filename)
        if _file is None:
            raise IndexError('File at path %s not found in report' % filename)
        return _file

    def __delitem__(self, filename):
        # remove from report
        _file = self._files.pop(filename)
        # remove chunks
        self._chunks[_file[0]] = None
        return True

    def get_folder_totals(self, path):
        """
        returns <ReportTotals> for files contained in a folder
        """
        path = path.strip('/') + '/'
        return sum_totals((self[filename].totals
                           for filename, _ in self._files.iteritems()
                           if filename.startswith(path)))

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
            for filename, data in self._files.iteritems():
                if not _path_filter(filename):
                    continue
                elif _line_modifier or data[1] is None:
                    # need to rebuild the file because there are line filters
                    yield self.get(filename).totals
                else:
                    yield data[1]

        totals = agg_totals(_iter_totals())
        if self._filter_cache and self._filter_cache[1]:
            flags = set(self._filter_cache[1])
            totals[9] = len([1
                             for _, session in self.sessions.iteritems()
                             if set(session.flags or []) & flags])
        else:
            totals[9] = len(self.sessions)

        return ReportTotals(*tuple(totals))

    @property
    def manifest(self):
        """returns a list of files in the report
        """
        if self._path_filter:
            return filter(self._path_filter, self._files.keys())

        else:
            return self._files.keys()

    def add_session(self, session):
        sessionid = len(self.sessions)
        self.sessions[sessionid] = session
        if self._totals:
            # add session to totals
            self._totals = self._totals._replace(sessions=sessionid+1)
        return sessionid, session

    def __iter__(self):
        """Iter through all the files
        yielding <ReportFile>
        """
        for filename, _file in self._files.iteritems():
            if self._path_filter and not self._path_filter(filename):
                # filtered out
                continue
            if self._chunks:
                report = self._chunks[_file[0]]
            else:
                report = None
            if isinstance(report, ReportFile):
                yield report
            else:
                yield self.file_class(name=filename,
                                      totals=_file[1],
                                      session_totals=_file[2] if len(_file) > 2 else None,
                                      lines=report,
                                      line_modifier=self._line_modifier)

    def __contains__(self, filename):
        return filename in self._files

    def merge(self, new_report, joined=True):
        """combine report data from another
        """
        if new_report is None:
            return

        elif not isinstance(new_report, Report):
            raise TypeError('expecting type Report got %s' % type(new_report))

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
            return len(filter(self._path_filter, self._files.keys())) == 0
        else:
            return len(self._files) == 0

    def __nonzero__(self):
        return self.is_empty() is False

    def to_archive(self):
        return END_OF_CHUNK.join(map(_encode_chunk, self._chunks)).encode("utf-8")

    def to_database(self):
        """returns (totals, report) to be stored in database
        """
        totals = dict(zip(TOTALS_MAP, self.totals))
        totals['diff'] = self.diff_totals
        return (totals,
                dumps({'files': self._files,
                       'sessions': self.sessions},
                      cls=ReportEncoder))

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
                ((_Change[0], _Change[5][5] if not _Change[1] and _Change[5] else None)
                 for _Change in changes)
            )
            # <dict path: stripeed if not in_diff>
            classes = dict(((_Change[0], 's') for _Change in changes if not _Change[3]))

            def _network():
                for name, _NetworkFile in self.network:
                    changed_coverage = changed_coverages.get(name)
                    if changed_coverage:
                        # changed file
                        yield name, ReportTotals(lines=_NetworkFile[0][1],
                                                 coverage=float(changed_coverage))
                    else:
                        diff = _NetworkFile.diff_totals
                        if diff and diff[1] > 0:  # lines > 0
                            # diff file
                            yield name, ReportTotals(lines=_NetworkFile[0][1],
                                                     coverage=-1 if float(diff[5]) < float(_NetworkFile[0][5]) else 1)

                        else:
                            # unchanged file
                            yield name, ReportTotals(lines=_NetworkFile[0][1])

            network = _network()

            def color(cov):
                return 'purple' if cov is None else \
                       '#e1e1e1' if cov == 0 else \
                       'green' if cov > 0 else \
                       'red'

        else:
            network = ((path, _NetworkFile[0])
                       for path, _NetworkFile
                       in self.network)
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
                    raise TypeError('expecting list for argument paths got %s' % type(paths))

                def _pf(filename):
                    return match(paths, filename)

                self._path_filter = _pf

            # flags: filter them out
            if flags:
                if not isinstance(flags, (list, set, tuple)):
                    flags = [flags]

                # get all session ids that have this falg
                sessions = set([int(sid)
                                for sid, session
                                in self.sessions.iteritems()
                                if match_any(flags, session.flags)])

                # the line has data from this session
                def adjust_line(line):
                    new_sessions = [LineSession(*s)
                                    for s in (line.sessions or [])
                                    if int(s[0]) in sessions]
                    # check if line is applicable
                    if not new_sessions:
                        return False
                    return ReportLine(coverage=get_coverage_from_sessions(new_sessions),
                                      complexity=get_complexity_from_sessions(new_sessions),
                                      type=line.type,
                                      sessions=new_sessions,
                                      messages=line.messages)

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
        if diff and diff.get('files'):
            for path, data in diff['files'].iteritems():
                future_state = Yaml.walk(future_diff, ('files', path, 'type'))
                if (
                    data['type'] == 'deleted' and  # deleted
                    path in self                   # and tracked
                ):
                    # found a file that was tracked and deleted
                    return True

                elif (
                    data['type'] == 'new' and      # newly tracked
                    future_state != 'deleted' and  # not deleted in future
                    path in future_report          # found in future
                ):
                    # newly tracked file
                    return True

                elif data['type'] == 'modified':
                    in_past = path in self
                    in_future = future_state != 'deleted' and path in future_report
                    if in_past and in_future:

                        # get the future version
                        future_file = future_report.get(path, bind=False)
                        # if modified
                        if future_state == 'modified':
                            # shift the lines to "guess" what C was
                            future_file.shift_lines_by_diff(future_diff['files'][path],
                                                            forward=False)

                        if self.get(path).does_diff_adjust_tracked_lines(data, future_file):
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
        if diff and diff.get('files'):
            for path, data in diff['files'].iteritems():
                if (
                    data['type'] == 'modified' and
                    path in self
                ):
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
        if diff and diff.get('files'):
            totals = []
            for path, data in diff['files'].iteritems():
                if data['type'] in ('modified', 'new'):
                    _file = self.get(path)
                    if _file:
                        fg = _file.get
                        lines = []
                        le = lines.extend
                        # add all new lines data to a new file to get totals
                        [le([fg(i)
                             for i, line in enumerate(filter(lambda l: l[0] != '-',
                                                             segment['lines']),
                                                      start=int(segment['header'][2]) or 1)
                             if line[0] == '+'])
                         for segment in data['segments']]

                        file_totals = ReportFile(name=None, totals=None, lines=lines).totals
                        totals.append(file_totals)
                        if _save:
                            data['totals'] = file_totals
                            # store in network
                            network_file = self._files[path]
                            if file_totals.lines == 0:
                                # no lines touched
                                file_totals = file_totals._replace(coverage=None,
                                                                   complexity=None,
                                                                   complexity_total=None)
                            self._files[path] = zfill(network_file, 3, file_totals)

            totals = sum_totals(totals)

            if totals.lines == 0:
                totals = totals._replace(coverage=None,
                                         complexity=None,
                                         complexity_total=None)

            if _save and totals.files:
                diff['totals'] = totals
                self.diff_totals = totals

            return totals

    def has_flag(self, flag_name):
        """
        Returns boolean: if the flag is found
        """
        for sid, data in self.sessions.iteritems():
            if flag_name in (data.flags or []):
                return True
        return False

    def assume_flags(self, flags, prev_report, name=None):
        with prev_report.filter(flags=flags) as filtered:
            # add the "assumed session"
            self.add_session(Session(
                flags=flags,
                totals=filtered.totals,
                name=name or 'Assumed'
            ))
            # merge the results
            self.merge(filtered)


def get_paths_from_flags(repository, flags):
    if flags:
        return list(set(list(chain(*[(Yaml.walk(repository, ('yaml', 'flags', flag, 'paths')) or [])
                                     for flag in flags]))))
    else:
        return []




def process_commit(commit, flags=None):
    if commit and commit['totals']:
        _commit = commit.pop('report', None) or {}
        _commit.setdefault('totals', commit.get('totals', None))
        _commit.setdefault('chunks', commit.pop('chunks', None))
        commit['report'] = Report(**_commit)
        if flags:
            commit['report'].filter(flags=flags)

    return commit
