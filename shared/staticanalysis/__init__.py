from shared.utils.enums import CodecovDatabaseEnum


class StaticAnalysisSingleFileSnapshotState(CodecovDatabaseEnum):
    created = 1
    valid = 2
    rejected = 3
