from shared.staticanalysis import StaticAnalysisSingleFileSnapshotState


def test_enum_choices():
    assert StaticAnalysisSingleFileSnapshotState.choices() == (
        (1, "CREATED"),
        (2, "VALID"),
        (3, "REJECTED"),
    )
