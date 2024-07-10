import abc


class ParserInterface(metaclass=abc.ABCMeta):
    @classmethod
    def __subclasshook__(cls, subclass):
        return hasattr(subclass, "parse") and callable(subclass.parse)
