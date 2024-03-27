from shared.utils.enums import CodecovDatabaseEnum


class UploadState(CodecovDatabaseEnum):
    UPLOADED = (1,)
    PROCESSED = (2,)
    ERROR = (3,)
    FULLY_OVERWRITTEN = (4,)
    PARTIALLY_OVERWRITTEN = (5,)
    PARALLEL_PROCESSED = (6,)

    def __init__(self, db_id):
        self.db_id = db_id


class UploadType(CodecovDatabaseEnum):
    UPLOADED = (1, "uploaded")
    CARRIEDFORWARD = (2, "carriedforward")

    def __init__(self, db_id, db_name):
        self.db_id = db_id
        self.db_name = db_name
