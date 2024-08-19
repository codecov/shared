from decimal import Decimal

import pytest

from shared.reports.types import ReportTotals
from shared.utils.ReportEncoder import ReportEncoder
from shared.utils.sessions import Session


@pytest.mark.unit
@pytest.mark.parametrize(
    "obj, res",
    [
        (ReportTotals(), (0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)),
        (
            ReportTotals("files", "lines"),
            ("files", "lines", 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
        ),
        (
            Session("id", "totals"),
            {
                "N": None,
                "a": None,
                "c": None,
                "e": None,
                "d": None,
                "f": None,
                "j": None,
                "n": None,
                "p": None,
                "u": None,
                "t": "totals",
                "st": "uploaded",
                "se": {},
            },
        ),
        (Decimal("85.00"), "85.00"),
    ],
)
def test_report_encoder(obj, res):
    assert ReportEncoder().default(obj) == res


@pytest.mark.unit
def test_exception_report_encoder():
    with pytest.raises(Exception) as e_info:
        ReportEncoder().default([1, 2])
    assert e_info.type is TypeError
