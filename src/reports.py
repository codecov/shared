from copy import copy
import types as ObjTypes
from src.utils.merge import *
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
from utils.ReportEncoder import ReportEncoder
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








_types = {
    ObjTypes.StringType: ObjTypes.StringType,
    ObjTypes.UnicodeType: ObjTypes.StringType,
    ObjTypes.LongType: ObjTypes.FloatType,
    ObjTypes.IntType: ObjTypes.FloatType,
    ObjTypes.FloatType: ObjTypes.FloatType,
    ObjTypes.ListType: ObjTypes.ListType,
    ObjTypes.BooleanType: ObjTypes.BooleanType
}.get



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


def get_paths_from_flags(repository, flags):
    if flags:
        return list(set(list(chain(*[(Yaml.walk(repository, ('yaml', 'flags', flag, 'paths')) or [])
                                     for flag in flags]))))
    else:
        return []
