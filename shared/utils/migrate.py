from json import loads

from shared.helpers.numeric import ratio

TOTALS_MAP = ("f", "n", "h", "m", "p", "c", "b", "d", "M", "s", "C", "N", "diff")
TOTALS_MAP_NAMES = (
    "files",
    "lines",
    "hits",
    "misses",
    "partials",
    "coverage",
    "branches",
    "methods",
    "messages",
    "sessions",
    "complexity",
    "complexity_total",
    "diff",
)
TOTALS_MAP_v1 = (
    "files",
    "lines",
    "hit",
    "missed",
    "partial",
    "coverage",
    "branches",
    "methods",
    "messages",
    "sessions",
    "complexity",
)


def migrate_totals(totals):
    if totals:
        if isinstance(totals, list):
            # v3
            return totals

        elif "hit" in totals:
            tg = totals.get
            # v1
            data = [tg(k, 0) for k in TOTALS_MAP_v1]
            data[5] = ratio(data[2], data[1])
            return data

        else:
            tg = totals.get if isinstance(totals, dict) else loads(totals).get
            # v2
            return [tg(k, 0) for k in TOTALS_MAP]
    return []
