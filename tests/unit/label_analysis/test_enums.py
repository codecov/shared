from shared.labelanalysis import LabelAnalysisRequestState


def test_enum_choices():
    assert LabelAnalysisRequestState.choices() == (
        (1, "CREATED"),
        (2, "FINISHED"),
        (3, "ERROR"),
    )


def test_enum_from_int():
    assert (
        LabelAnalysisRequestState.enum_from_int(1) == LabelAnalysisRequestState.CREATED
    )
    assert (
        LabelAnalysisRequestState.enum_from_int(2) == LabelAnalysisRequestState.FINISHED
    )
    assert LabelAnalysisRequestState.enum_from_int(3) == LabelAnalysisRequestState.ERROR
    assert LabelAnalysisRequestState.enum_from_int(4) is None
