import dataclasses
from fractions import Fraction
from json import JSONEncoder
from types import GeneratorType

from shared.reports.types import ReportTotals
from shared.reports.types.totals import SessionTotalsArray


class ReportEncoder(JSONEncoder):
    separators = (",", ":")

    def default(self, obj):
        if dataclasses.is_dataclass(obj):
            return obj.astuple()
        elif isinstance(obj, Fraction):
            return str(obj)
        elif isinstance(obj, ReportTotals):
            # reduce totals
            obj = list(obj)
            while obj and obj[-1] in ("0", 0):
                obj.pop()
            return obj
        elif isinstance(obj, SessionTotalsArray):
            return obj.to_database()
        elif hasattr(obj, "_encode"):
            return obj._encode()
        elif isinstance(obj, GeneratorType):
            obj = list(obj)
        # let the base class default method raise the typeerror
        return JSONEncoder.default(self, obj)
