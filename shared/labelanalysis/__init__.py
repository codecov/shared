from shared.utils.enums import CodecovDatabaseEnum


class LabelAnalysisRequestState(CodecovDatabaseEnum):
    CREATED = (1,)
    FINISHED = (2,)
    ERROR = (3,)

    def __init__(self, db_id):
        self.db_id = db_id
