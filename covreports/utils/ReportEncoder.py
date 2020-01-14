from json import JSONEncoder
from types import GeneratorType
from fractions import Fraction
from covreports.reports.types import ReportTotals
import dataclasses


class ReportEncoder(JSONEncoder):
    separators = (',', ':')

    def default(self, obj):
        if dataclasses.is_dataclass(obj):
            return dataclasses.astuple(obj)
        if isinstance(obj, Fraction):
            return str(obj)
        if isinstance(obj, ReportTotals):
            # reduce totals
            obj = list(obj)
            while obj and obj[-1] in ('0', 0):
                obj.pop()
            return obj
        elif hasattr(obj, '_encode'):
            return obj._encode()
        elif isinstance(obj, GeneratorType):
            obj = list(obj)
        # let the base class default method raise the typeerror
        return JSONEncoder.default(self, obj)
