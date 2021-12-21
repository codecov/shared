from enum import Enum


class CodecovDatabaseEnum(Enum):
    @classmethod
    def choices(cls):
        return tuple((i.value, i.name) for i in cls)


class UploadState(CodecovDatabaseEnum):
    uploaded = 1
    processed = 2
    error = 3


class UploadType(CodecovDatabaseEnum):
    uploaded = 1
    carryforwarded = 2
