from __future__ import annotations

import dataclasses
from decimal import Decimal
from fractions import Fraction
from types import GeneratorType
from typing import TYPE_CHECKING

import orjson
import sentry_sdk

from .reportfile import ReportFile
from .types import ReportLine, ReportTotals

if TYPE_CHECKING:
    from .resources import Report


END_OF_CHUNK = "\n<<<<< end_of_chunk >>>>>\n"
END_OF_HEADER = "\n<<<<< end_of_header >>>>>\n"


@sentry_sdk.trace
def serialize_report(
    report: Report, with_totals=True
) -> tuple[bytes, bytes, ReportTotals | None]:
    """
    Serializes a report as `(report_json, chunks, totals)`.

    The `totals` is either a `ReportTotals`, or `None`, depending on the `with_totals` flag.
    """

    indexed_files = list(enumerate(report._files.values()))

    chunks = (
        orjson.dumps(report._header, option=orjson_option).decode()
        + END_OF_HEADER
        + END_OF_CHUNK.join(_encode_chunk(file) for i, file in indexed_files)
    )

    if with_totals:
        totals = report.totals
        totals.diff = report.diff_totals

        files = {
            file.name: [i, file.totals, None, file.diff_totals]
            for i, file in indexed_files
        }
    else:
        totals = None

        files = {file.name: [i, None] for i, file in indexed_files}

    report_json = orjson.dumps(
        {"files": files, "sessions": report.sessions, "totals": totals},
        default=report_default,
        option=orjson_option,
    )

    return (report_json, chunks.encode(), totals)


def report_default(obj):
    if dataclasses.is_dataclass(obj):
        return obj.astuple()
    elif isinstance(obj, Fraction):
        return str(obj)
    elif isinstance(obj, Decimal):
        return str(obj)
    elif isinstance(obj, ReportTotals):
        # reduce totals
        return obj.to_database()
    elif hasattr(obj, "_encode"):
        return obj._encode()
    elif isinstance(obj, GeneratorType):
        obj = list(obj)
    # let the base class default method raise the typeerror
    return obj


orjson_option = orjson.OPT_PASSTHROUGH_DATACLASS | orjson.OPT_NON_STR_KEYS


def _dumps_not_none(value) -> str:
    if isinstance(value, list):
        return orjson.dumps(
            _rstrip_none(list(value)), default=report_default, option=orjson_option
        ).decode()
    if isinstance(value, ReportLine):
        return orjson.dumps(
            _rstrip_none(list(value.astuple())),
            default=report_default,
            option=orjson_option,
        ).decode()
    return value if value and value != "null" else ""


def _rstrip_none(lst):
    while lst[-1] is None:
        lst.pop(-1)
    return lst


def chunk_default(obj):
    if dataclasses.is_dataclass(obj):
        return obj.astuple()
    return obj


def _encode_chunk(chunk) -> str:
    if chunk is None:
        return "null"
    elif isinstance(chunk, ReportFile):
        if isinstance(chunk._raw_lines, str):
            return chunk._raw_lines
        else:
            return (
                orjson.dumps(chunk.details, option=orjson_option).decode()
                + "\n"
                + "\n".join(_dumps_not_none(line) for line in chunk._lines)
            )
    elif isinstance(chunk, (list, dict)):
        return orjson.dumps(chunk, default=chunk_default, option=orjson_option).decode()
    else:
        return chunk
