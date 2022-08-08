from shared.utils.enums import CodecovDatabaseEnum


class UploadState(CodecovDatabaseEnum):
    uploaded = 1
    processed = 2
    error = 3


class UploadType(CodecovDatabaseEnum):
    uploaded = 1
    carryforwarded = 2
