import dataclasses
from decimal import Decimal
from fractions import Fraction
from types import GeneratorType

import orjson

from shared.reports.types import ReportTotals


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
