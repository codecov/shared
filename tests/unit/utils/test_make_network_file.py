import pytest

from shared.reports.types import NetworkFile, ReportTotals
from shared.utils.make_network_file import make_network_file


@pytest.mark.unit
def test_make_network_file():
    assert make_network_file([1, 2, 1, 1]) == NetworkFile(
        totals=ReportTotals(
            files=1,
            lines=2,
            hits=1,
            misses=1,
            partials=0,
            complexity=0,
            complexity_total=0,
            diff=0,
        ),
        diff_totals=None,
    )


def test_make_network_file_with_sessions_encoded():
    assert make_network_file([1, 2, 1, 1]) == NetworkFile(
        totals=ReportTotals(
            files=1,
            lines=2,
            hits=1,
            misses=1,
            partials=0,
            complexity=0,
            complexity_total=0,
            diff=0,
        ),
        diff_totals=None,
    )
