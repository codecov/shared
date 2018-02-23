from src.utils.tuples import ReportTotals
from src.helpers.ratio import ratio
from itertools import chain, groupby, izip_longest, izip, imap, starmap



def agg_totals(totals):
    totals = filter(None, totals)
    n_files = len(totals)
    totals = list(imap(_sum, izip(*totals)))
    if not totals:
        return list(ReportTotals.__new__.__defaults__)
    totals[0] = n_files
    totals[5] = ratio(totals[2], totals[1])
    return totals
