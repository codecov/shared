from shared.staticanalysis import StaticAnalysisSingleFileSnapshotState


def test_enum_choices():
    assert StaticAnalysisSingleFileSnapshotState.choices() == (
        (1, "created"),
        (2, "valid"),
        (3, "rejected"),
    )
