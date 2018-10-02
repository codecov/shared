from collections import defaultdict
from itertools import groupby, starmap
from covreports.utils.tuples import ReportLine
from covreports.utils.tuples import LineSession


def merge_all(coverages, missing_branches=None):
    if len(coverages) == 1:
        return coverages[0]

    cov = coverages[0]
    for _ in coverages[1:]:
        cov = merge_coverage(cov, _, missing_branches)
    return cov


def merge_branch(b1, b2):
    if b1 == b2:  # 1/2 == 1/2
        return b1
    elif b1 == -1 or b2 == -1:
        return -1
    elif type(b1) in (int, int) and b1 > 0:
        return b1
    elif type(b2) in (int, int) and b2 > 0:
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


def merge_partial_line(p1, p2):
    if not p1 or not p2:
        return p1 or p2

    np = p1 + p2
    if len(np) == 1:
        # one result already
        return np

    fl = defaultdict(list)
    [[fl[x].append(_c) for x in range(_s or 0, _e + 1)] for _s, _e, _c in np if _e is not None]
    ks = list(fl.keys())
    mx = max(ks)+1 if ks else 0
    # appends coverage on each column when [X, None, C]
    [[fl[x].append(_c) for x in range(_s or 0, mx)] for _s, _e, _c in np if _e is None]
    ks = list(fl.keys())
    # fl = {1: [1], 2: [1], 4: [0], 3: [1], 5: [0], 7: [0], 8: [0]}
    pp = []
    append = pp.append
    print("####" * 20)
    print(str(list(fl.items())))
    for cov, group in groupby(sorted([(cl, max(cv)) for cl, cv in list(fl.items())]), lambda c: c[1]):
        group = list(group)
        append(_ifg(group[0][0], group[-1][0], cov))

    # never ends
    if [[max(ks), None, _c] for _s, _e, _c in np if _e is None]:
        pp[-1][1] = None

    return pp


def merge_coverage(l1, l2, branches_missing=True):
    if l1 is None or l2 is None:
        return l1 if l1 is not None else l2

    elif l1 == -1 or l2 == -1:
        # ignored line
        return -1

    l1t = cast_ints_float(l1)
    l2t = cast_ints_float(l2)

    if isinstance(l1t, float) and isinstance(l2t, float):
        return l1 if l1 >= l2 else l2

    elif isinstance(l1t, str) or isinstance(l2t, str):
        if isinstance(l1t, float):
            # using or here because if l1 is 0 return l2
            # this will trigger 100% if l1 is > 0
            branches_missing = [] if l1 else False
            l1 = l2

        elif isinstance(l2t, float):
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

    elif isinstance(l1t, list) and isinstance(l2t, list):
        return merge_partial_line(l1, l2)

    elif isinstance(l1t, bool) or isinstance(l2t, bool):
        return (l2 or l1) if isinstance(l1t, bool) else (l1 or l2)

    return merge_coverage(partials_to_line(l1) if isinstance(l1t, list) else l1,
                          partials_to_line(l2) if isinstance(l2t, list) else l2)


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
            mb = [_f for _f in mb if _f]
            # # no branch data provided
            # if not mb:
            #     return []

            # we only have one missing branches data
            if len(mb) == 1:
                return mb[0]

            else:
                # combine the branches
                mb = list(map(set, mb))
                m1 = mb.pop(0)
                for m in mb:
                    m1 = m1 & m
                return list(m1)


def merge_line(l1, l2, joined=True):
    if not l1 or not l2:
        return l1 or l2

    # merge sessions
    sessions = _merge_sessions(list(l1.sessions or []), list(l2.sessions or []))

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


def _merge_sessions(s1, s2):
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
        s1 = list(s1.values()) + list(s2.values())

    else:
        s1.extend(s2)

    return list(starmap(LineSession, s1))


def _ifg(s, e, c):
    """
    s=start, e=end, c=coverage
    Insures the end is larger then the start.
    """
    return [s, e if e > s else s+1, c]

def cast_ints_float(value):
    """
    When doing a merge we'd like to convert all ints to floats. this method takes in a value and
    converts it to flaot if type(value) is int
    """
    return value if type(value) is not int else float(value)

def line_type(line):
    """
    -1 = skipped (had coverage data, but fixed out)
    0 = hit
    1 = miss
    2 = partial
    None = ignore (because it has messages or something)
    """
    return 2 if line is True else \
        branch_type(line) if type(line) is (str,) else \
            -1 if line == -1 else \
                None if line is False else \
                    0 if line else \
                        1 if line is not None else None


def branch_type(b):
    """
    0 = hit
    1 = miss
    2 = partial
    """
    b1, b2 = tuple(b.split('/', 1))
    return 0 if b1 == b2 else 1 if b1 == '0' else 2


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


def get_complexity_from_sessions(sessions):
    _type = type(sessions[0][4])
    if _type is int:
        return max([(s[4] or 0) for s in sessions])
    elif _type in (tuple, list):
        return (max([(s[4] or (0, 0))[0] for s in sessions]),
                max([(s[4] or (0, 0))[1] for s in sessions]))


def get_coverage_from_sessions(sessions):
    return merge_all([s[1] for s in sessions], merge_missed_branches(sessions))
