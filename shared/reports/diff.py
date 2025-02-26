import dataclasses
from typing import Generator, Literal, Protocol, TypedDict

from shared.reports.totals import get_line_totals
from shared.reports.types import ReportLine, ReportTotals
from shared.utils.totals import sum_totals


class DiffSegment(TypedDict):
    lines: list[str]
    """The lines within a diff segment, prefixed with "+" or "-" for added/removed lines, or " " for context."""
    header: tuple[int, int, int, int]
    """The segment header, which is `old_line`, `old_length`, `new_line`, `new_length`."""


class DiffFile(TypedDict):
    type: Literal["new", "modified", "deleted"]
    "Whether the file was added, removed or modified in this diff."
    segments: list[DiffSegment]
    """A list of diff segments, or "hunk"s as they are also called."""


class RawDiff(TypedDict):
    files: dict[str, DiffFile]
    "This is a dictionary from path to `DiffFile`."


class CalculatedDiff(TypedDict):
    general: ReportTotals
    "The totals across this diff"
    files: dict[str, ReportTotals]
    "Per-file totals, keyed by path."


# TODO: it might make sense to move these abstract interfaces to a different place
class AbstractReportFile(Protocol):
    def get(self, line_no: int) -> ReportLine | None:
        "Get the line specified by `line_no` (1-indexed), or `None` if the line does not exist."
        ...

    def calculate_diff(self, segments: list[DiffSegment]) -> ReportTotals:
        "Calculates the totals for the given diff `segments`."
        ...


class AbstractReport(Protocol):
    def get(self, path: str) -> AbstractReportFile | None:
        "Get the file using its `path` within the Report, or `None` if no such file exists."
        ...


def relevant_lines(segment: DiffSegment) -> Generator[int, None, None]:
    "Iterates over the relevant line numbers in a diff segment."
    return (
        i
        for i, line in enumerate(
            (ln for ln in segment["lines"] if ln[0] != "-"),
            start=int(segment["header"][2]) or 1,
        )
        if line[0] == "+"
    )


def calculate_file_diff(
    file: AbstractReportFile, segments: list[DiffSegment]
) -> ReportTotals:
    """
    Calculates the `ReportTotals` across all relevant lines in the diff `segments`.

    Takes a line accessor `get_line` returning an optional `ReportLine`
    for a given line number.
    """

    line_numbers = (i for segment in segments for i in relevant_lines(segment))
    lines = (file.get(ln) for ln in line_numbers)
    return get_line_totals(line for line in lines if line)


def calculate_report_diff(report: AbstractReport, diff: RawDiff) -> CalculatedDiff:
    """
    Calculates the `ReportTotals` across a complete Report, as well as per-file,
    for all files present in the `diff`.

    Takes a callback function that calculates the per-file totals given a file path.
    """

    files: dict[str, ReportTotals] = {}
    # TODO: update `totals` in-place
    list_of_file_totals = []

    for path, data in diff["files"].items():
        if data["type"] in ("modified", "new"):
            file = report.get(path)
            if file:
                file_totals = calculate_file_diff(file, data["segments"])
                files[path] = file_totals
                list_of_file_totals.append(file_totals)

    totals = sum_totals(list_of_file_totals)

    if totals.lines == 0:
        totals = dataclasses.replace(
            totals, coverage=None, complexity=None, complexity_total=None
        )

    return CalculatedDiff(general=totals, files=files)
