from enum import Enum


class CodecovDatabaseEnum(Enum):
    @classmethod
    def choices(cls):
        return tuple((i.value, i.name) for i in cls)

    @classmethod
    def enum_from_int(cls, value):
        for elem in cls:
            if elem.value == value:
                return elem
        return None
