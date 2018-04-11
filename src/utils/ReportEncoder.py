from json import JSONEncoder
from types import GeneratorType
from src.utils.tuples import ReportTotals


class ReportEncoder(JSONEncoder):
    separators = (',', ':')

    def default(self, obj):
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
