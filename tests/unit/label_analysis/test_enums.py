from shared.labelanalysis import LabelAnalysisRequestState


def test_enum_choices():
    assert LabelAnalysisRequestState.choices() == (
        (1, "created"),
        (2, "finished"),
        (3, "error"),
    )


def test_enum_from_int():
    assert (
        LabelAnalysisRequestState.enum_from_int(1) == LabelAnalysisRequestState.created
    )
    assert (
        LabelAnalysisRequestState.enum_from_int(2) == LabelAnalysisRequestState.finished
    )
    assert LabelAnalysisRequestState.enum_from_int(3) == LabelAnalysisRequestState.error
    assert LabelAnalysisRequestState.enum_from_int(4) is None
