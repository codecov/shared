from json import JSONEncoder
from src.utils.tuples import ReportTotals
from src.ReportFile import ReportFile
from src.helpers.sessions import Session
import types as ObjTypes


class ReportEncoder(JSONEncoder):
    separators = (',', ':')

    def default(self, obj):
        if isinstance(obj, ReportTotals):
            # reduce totals
            obj = list(obj)
            while obj and obj[-1] in ('0', 0):
                obj.pop()
            return obj
        elif isinstance(obj, (Session, ReportFile)):
            return obj._encode()
        elif isinstance(obj, ObjTypes.GeneratorType):
            obj = list(obj)
        # let the base class default method raise the typeerror
        return JSONEncoder.default(self, obj)

