import pytest

from shared.reports.types import ReportTotals
from shared.utils.flare import report_to_flare


@pytest.mark.unit
def test_report_to_flare():
    files = [
        ("a/b/c.py", ReportTotals(None, 100, 47, None, None, "47.00000")),
        ("a/b/d.py", ReportTotals(None, 100, 20, None, None, "20.00000")),
        ("a/b/e.py", ReportTotals(None, 100, 30, None, None, "30.00000")),
        ("x/y/z", ReportTotals(None, 100, 40, None, None, "40.00000")),
        ("a/b/c/d/e.py", ReportTotals(None, 100, 40, None, None, "40.00000")),
        ("a/b/c/d/g.py", ReportTotals(None, 100, 60, None, None, "60.00000")),
        ("a.py", ReportTotals(None, 100, 70, None, None, "70.00000")),
        ("b.py", ReportTotals(None, 100, 80, None, None, "80.00000")),
    ]

    expected_result = [
        {
            "name": "",
            "coverage": 48.375,
            "color": "#c6b11a",
            "_class": None,
            "lines": 800,
            "children": [
                {
                    "name": "a/b",
                    "coverage": 39.4,
                    "color": "#dfb317",
                    "_class": None,
                    "lines": 500,
                    "children": [
                        {
                            "name": "c/d",
                            "coverage": 50.0,
                            "color": "#c0b01b",
                            "_class": None,
                            "lines": 200,
                            "children": [
                                {
                                    "color": "#dfb317",
                                    "_class": None,
                                    "lines": 100,
                                    "name": "e.py",
                                    "coverage": "40.00000",
                                },
                                {
                                    "color": "#a4a61d",
                                    "_class": None,
                                    "lines": 100,
                                    "name": "g.py",
                                    "coverage": "60.00000",
                                },
                            ],
                        },
                        {
                            "color": "#f39a21",
                            "_class": None,
                            "lines": 100,
                            "name": "e.py",
                            "coverage": "30.00000",
                        },
                        {
                            "color": "#c9b21a",
                            "_class": None,
                            "lines": 100,
                            "name": "c.py",
                            "coverage": "47.00000",
                        },
                        {
                            "color": "#fe7d37",
                            "_class": None,
                            "lines": 100,
                            "name": "d.py",
                            "coverage": "20.00000",
                        },
                    ],
                },
                {
                    "color": "#97ca00",
                    "_class": None,
                    "lines": 100,
                    "name": "b.py",
                    "coverage": "80.00000",
                },
                {
                    "color": "#a1b90e",
                    "_class": None,
                    "lines": 100,
                    "name": "a.py",
                    "coverage": "70.00000",
                },
                {
                    "name": "x/y",
                    "coverage": 40.0,
                    "color": "#dfb317",
                    "_class": None,
                    "lines": 100,
                    "children": [
                        {
                            "color": "#dfb317",
                            "_class": None,
                            "lines": 100,
                            "name": "z",
                            "coverage": "40.00000",
                        }
                    ],
                },
            ],
        }
    ]

    def _compare_nested_children_node(result, excpected):
        """
        helper method to compare nested dicts, if an item of a dict is a list, the list is sorted and then compared
        agaisnt the expected result
        """
        if isinstance(result, list):
            sorted_list = sorted(result, key=lambda k: k["name"])
            sorted_expected = sorted(excpected, key=lambda k: k["name"])
            for i in range(len(sorted_list)):
                _compare_nested_children_node(sorted_list[i], sorted_expected[i])
        else:
            for key in result.keys():
                if key == "children":
                    _compare_nested_children_node(
                        result["children"], excpected["children"]
                    )
                else:
                    assert result[key] == excpected[key]

    report_results = report_to_flare(files, [0, 100])
    assert len(expected_result) == len(report_results)
    for i in range(len(expected_result)):
        _compare_nested_children_node(expected_result, report_results)
