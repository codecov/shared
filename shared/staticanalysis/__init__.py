from shared.utils.enums import CodecovDatabaseEnum


class StaticAnalysisSingleFileSnapshotState(CodecovDatabaseEnum):
    CREATED = (1,)
    VALID = (2,)
    REJECTED = (3,)

    def __init__(self, db_id):
        self.db_id = db_id
