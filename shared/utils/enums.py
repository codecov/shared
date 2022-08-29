from enum import Enum


class CodecovDatabaseEnum(Enum):
    @classmethod
    def choices(cls):
        return tuple((i.db_id, i.name) for i in cls)

    @classmethod
    def enum_from_int(cls, value):
        for elem in cls:
            if elem.db_id == value:
                return elem
        return None
