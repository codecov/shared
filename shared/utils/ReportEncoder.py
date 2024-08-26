import dataclasses
from decimal import Decimal
from fractions import Fraction
from json import JSONEncoder
from types import GeneratorType

from shared.reports.types import ReportTotals


class ReportEncoder(JSONEncoder):
    separators = (",", ":")

    def default(self, obj):
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
        return JSONEncoder.default(self, obj)
