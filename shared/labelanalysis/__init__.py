from shared.utils.enums import CodecovDatabaseEnum


class LabelAnalysisRequestState(CodecovDatabaseEnum):
    created = 1
    finished = 2
    error = 3
