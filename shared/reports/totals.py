from typing import Iterator

from shared.helpers.numeric import ratio
from shared.reports.types import ReportLine, ReportTotals
from shared.utils.merge import LineType as Coverage
from shared.utils.merge import line_type as coverage_type


def get_line_totals(lines: Iterator[ReportLine]) -> ReportTotals:
    """
    Calculates the totals (`ReportTotals`) across all the given `lines` (`ReportLine`s).
    """
    hits = 0
    misses = 0
    partials = 0
    branches = 0
    methods = 0
    messages = 0
    complexity = 0
    complexity_total = 0

    for line in lines:
        match coverage_type(line.coverage):
            case Coverage.hit:
                hits += 1
            case Coverage.miss:
                misses += 1
            case Coverage.partial:
                partials += 1

        if line.type == "b":
            branches += 1
        elif line.type == "m":
            methods += 1

        if line.messages:
            messages += len(line.messages)

        if isinstance(line.complexity, int):
            complexity += line.complexity
        elif line.complexity:
            complexity += line.complexity[0]
            complexity_total += line.complexity[1]

    total_lines = hits + misses + partials

    return ReportTotals(
        files=0,
        lines=total_lines,
        hits=hits,
        misses=misses,
        partials=partials,
        coverage=ratio(hits, total_lines) if total_lines else None,
        branches=branches,
        methods=methods,
        messages=messages,
        sessions=0,
        complexity=complexity,
        complexity_total=complexity_total,
    )
