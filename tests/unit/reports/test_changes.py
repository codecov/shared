from pathlib import Path


import pytest

from shared.reports.types import Change
from shared.reports.changes import get_changes_using_rust, run_comparison_using_rust

from shared.reports.readonly import ReadOnlyReport, rustify_diff, LazyRustReport
from shared.reports.types import ReportTotals, ReportLine, LineSession
from shared.reports.resources import ReportFile

current_file = Path(__file__)


@pytest.fixture
def sample_rust_report(mocker):
    mocker.patch.object(ReadOnlyReport, "should_load_rust_version", return_value=True)
    with open(current_file.parent / "samples" / "chunks_01.txt", "r") as f:
        chunks = f.read()
    files_dict = {
        "awesome/__init__.py": [
            2,
            [0, 10, 8, 2, 0, "80.00000", 0, 0, 0, 0, 0, 0, 0],
            [[0, 10, 8, 2, 0, "80.00000", 0, 0, 0, 0, 0, 0, 0]],
            [0, 2, 1, 1, 0, "50.00000", 0, 0, 0, 0, 0, 0, 0],
        ],
        "tests/__init__.py": [
            0,
            [0, 3, 2, 1, 0, "66.66667", 0, 0, 0, 0, 0, 0, 0],
            [[0, 3, 2, 1, 0, "66.66667", 0, 0, 0, 0, 0, 0, 0]],
            None,
        ],
        "tests/test_sample.py": [
            1,
            [0, 7, 7, 0, 0, "100", 0, 0, 0, 0, 0, 0, 0],
            [[0, 7, 7, 0, 0, "100", 0, 0, 0, 0, 0, 0, 0]],
            None,
        ],
    }
    sessions_dict = {
        "0": {
            "N": None,
            "a": "v4/raw/2019-01-10/4434BC2A2EC4FCA57F77B473D83F928C/abf6d4df662c47e32460020ab14abf9303581429/9ccc55a1-8b41-4bb1-a946-ee7a33a7fb56.txt",
            "c": None,
            "d": 1547084427,
            "e": None,
            "f": ["unit"],
            "j": None,
            "n": None,
            "p": None,
            "t": [3, 20, 17, 3, 0, "85.00000", 0, 0, 0, 0, 0, 0, 0],
            "": None,
        }
    }
    return ReadOnlyReport.from_chunks(
        chunks=chunks, files=files_dict, sessions=sessions_dict
    )


def test_run_comparison_using_rust(sample_rust_report):
    base_report, head_report = sample_rust_report, sample_rust_report
    diff = {
        "files": {
            "tests/__init__.py": {
                "type": "modified",
                "before": None,
                "segments": [
                    {
                        "header": ["1", "3", "1", "5"],
                        "lines": [
                            "+sudo: false",
                            "+",
                            " language: python",
                            " ",
                            " python:",
                        ],
                    }
                ],
                "stats": {"added": 2, "removed": 0},
            }
        }
    }
    k = run_comparison_using_rust(base_report, head_report, diff)
    print(k)
    assert k == {
        "files": [
            {
                "base_name": "tests/__init__.py",
                "head_name": "tests/__init__.py",
                "file_was_added_by_diff": False,
                "file_was_removed_by_diff": False,
                "base_coverage": {
                    "hits": 2,
                    "misses": 1,
                    "partials": 0,
                    "branches": 0,
                    "sessions": 0,
                    "complexity": 0,
                    "complexity_total": 0,
                    "methods": 0,
                },
                "head_coverage": {
                    "hits": 2,
                    "misses": 1,
                    "partials": 0,
                    "branches": 0,
                    "sessions": 0,
                    "complexity": 0,
                    "complexity_total": 0,
                    "methods": 0,
                },
                "removed_diff_coverage": [],
                "added_diff_coverage": [[1, "h"]],
                "unexpected_line_changes": [
                    [[1, "h"], [3, None]],
                    [[2, None], [4, "h"]],
                    [[3, None], [5, "m"]],
                    [[4, "h"], [6, None]],
                    [[5, "m"], [7, None]],
                ],
            }
        ],
        "changes_summary": {"patch_totals": {"hits": 1, "misses": 0, "partials": 0}},
    }


def test_get_changes_using_rust(sample_rust_report):
    base_report, head_report = sample_rust_report, sample_rust_report
    diff = {
        "files": {
            "tests/__init__.py": {
                "type": "modified",
                "before": None,
                "segments": [
                    {
                        "header": ["1", "3", "1", "5"],
                        "lines": [
                            "+sudo: false",
                            "+",
                            " language: python",
                            " ",
                            " python:",
                        ],
                    }
                ],
                "stats": {"added": 2, "removed": 0},
            }
        }
    }
    k = get_changes_using_rust(base_report, head_report, diff)
    print(k)
    assert k == [
        Change(
            path="tests/__init__.py",
            new=False,
            deleted=False,
            in_diff=True,
            old_path=None,
            totals=None,
        )
    ]
