from shared.reports.enums import UploadState, UploadType


def test_enums():
    assert UploadState.choices() == ((1, "uploaded"), (2, "processed"), (3, "error"))
    assert UploadType.choices() == ((1, "uploaded"), (2, "carryforwarded"))
