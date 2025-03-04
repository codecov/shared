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


END_OF_CHUNK = b"\n<<<<< end_of_chunk >>>>>\n"
END_OF_HEADER = b"\n<<<<< end_of_header >>>>>\n"


@sentry_sdk.trace
def serialize_report(
    report: Report, with_totals=True
) -> tuple[bytes, bytes, ReportTotals | None]:
    """
    Serializes a report as `(report_json, chunks, totals)`.

    The `totals` is either a `ReportTotals`, or `None`, depending on the `with_totals` flag.
    """

    chunks = orjson.dumps(report._header, option=orjson_option)
    chunks += END_OF_HEADER
    for i, chunk in enumerate(report._chunks):
        if i > 0:
            chunks += END_OF_CHUNK
        chunks += _encode_chunk(chunk)

    if with_totals:
        totals = report.totals
        totals.diff = report.diff_totals
    else:
        totals = None

    report_json = orjson.dumps(
        {"files": report._files, "sessions": report.sessions, "totals": totals},
        default=report_default,
        option=orjson_option,
    )

    return (report_json, chunks, totals)


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


def _dumps_not_none(value) -> bytes:
    if isinstance(value, list):
        return orjson.dumps(
            _rstrip_none(list(value)), default=report_default, option=orjson_option
        )
    if isinstance(value, ReportLine):
        return orjson.dumps(
            _rstrip_none(list(value.astuple())),
            default=report_default,
            option=orjson_option,
        )
    return value.encode() if value and value != "null" else b""


def _rstrip_none(lst):
    while lst[-1] is None:
        lst.pop(-1)
    return lst


def chunk_default(obj):
    if dataclasses.is_dataclass(obj):
        return obj.astuple()
    return obj


def _encode_chunk(chunk) -> bytes:
    if chunk is None:
        return b"null"
    elif isinstance(chunk, ReportFile):
        encoded = orjson.dumps(chunk.details, option=orjson_option)
        encoded += b"\n"
        for i, line in enumerate(chunk._lines):
            if i > 0:
                encoded += b"\n"
            encoded += _dumps_not_none(line)

        return encoded
    elif isinstance(chunk, (list, dict)):
        return orjson.dumps(chunk, default=chunk_default, option=orjson_option)
    elif isinstance(chunk, str):
        return chunk.encode()
    else:
        return chunk
