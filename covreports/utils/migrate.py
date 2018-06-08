from json import loads
from itertools import izip_longest
from covreports.helpers.ratio import ratio


TOTALS_MAP = ('f', 'n', 'h', 'm', 'p', 'c', 'b', 'd', 'M', 's', 'C', 'N', 'diff')
TOTALS_MAP_NAMES = ('files', 'lines', 'hits', 'misses', 'partials', 'coverage',
                    'branches', 'methods', 'messages', 'sessions',
                    'complexity', 'complexity_total', 'diff')
TOTALS_MAP_v1 = ('files', 'lines', 'hit', 'missed', 'partial',
                 'coverage', 'branches', 'methods', 'messages', 'sessions', 'complexity')


def migrate_totals(totals):
    if totals:
        if type(totals) is list:
            # v3
            return totals

        elif 'hit' in totals:
            tg = totals.get
            # v1
            data = [tg(k, 0) for k in TOTALS_MAP_v1]
            data[5] = ratio(data[2], data[1])
            return data

        else:
            tg = totals.get if type(totals) is dict else loads(totals).get
            # v2
            return [tg(k, 0) for k in TOTALS_MAP]
    return []


def v3_to_v2(report, path=None):
    # used for extension
    return {'files': dict([(f.name, {'l': dict([(str(ln), line.coverage)
                                                for ln, line in f.lines]),
                                     't': dict(zip(TOTALS_MAP, list(f.totals)))})
                           for f in report
                           if not path or path == f.name]),
            'totals': dict(zip(TOTALS_MAP, list(report.totals)))}


def totals_to_dict(totals):
    if type(totals) is dict:
        # turn into list for zipping
        totals = [totals.get(k, 0) for k in TOTALS_MAP]

    totals = dict(izip_longest(TOTALS_MAP_NAMES, totals,
                  fillvalue=0))

    totals['coverage'] = float(totals['coverage'])
    return totals
