from pathlib import Path

import pytest
from cc_rustyribs import rustify_diff

from shared.reports.changes import (
    _get_changes_from_comparison,
    get_changes_using_rust,
    run_comparison_using_rust,
)
from shared.reports.readonly import ReadOnlyReport
from shared.reports.types import Change

current_file = Path(__file__)


@pytest.fixture
def sample_rust_report(mocker):
    mocker.patch.object(ReadOnlyReport, "should_load_rust_version", return_value=True)
    with open(current_file.parent / "samples" / "chunks_01.txt", "r") as f:
        chunks = f.read()
    files_dict = {
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
        "awesome/__init__.py": [
            2,
            [0, 10, 8, 2, 0, "80.00000", 0, 0, 0, 0, 0, 0, 0],
            [[0, 10, 8, 2, 0, "80.00000", 0, 0, 0, 0, 0, 0, 0]],
            [0, 2, 1, 1, 0, "50.00000", 0, 0, 0, 0, 0, 0, 0],
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
                "lines_only_on_base": [],
                "lines_only_on_head": [1, 2],
            }
        ],
        "changes_summary": {
            "patch_totals": {"hits": 1, "misses": 0, "partials": 0, "coverage": 1}
        },
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


def test_get_changes_from_comparison(mocker):
    res = _get_changes_from_comparison(
        {
            "files": [
                {
                    "base_name": "ProgressBar/index.tsx",
                    "head_name": "ProgressBar/index.tsx",
                    "file_was_added_by_diff": False,
                    "file_was_removed_by_diff": False,
                    "base_coverage": {
                        "hits": 29,
                        "misses": 0,
                        "partials": 0,
                        "branches": 4,
                        "sessions": 0,
                        "complexity": 0,
                        "complexity_total": 0,
                        "methods": 4,
                    },
                    "head_coverage": {
                        "hits": 29,
                        "misses": 0,
                        "partials": 0,
                        "branches": 4,
                        "sessions": 0,
                        "complexity": 0,
                        "complexity_total": 0,
                        "methods": 4,
                    },
                    "removed_diff_coverage": [[8, "h"]],
                    "added_diff_coverage": [[8, "h"]],
                    "unexpected_line_changes": [],
                },
                {
                    "base_name": "ProgressBar/ui.model.ts",
                    "head_name": "ProgressBar/data.qa.ts",
                    "file_was_added_by_diff": False,
                    "file_was_removed_by_diff": False,
                    "base_coverage": None,
                    "head_coverage": {
                        "hits": 2,
                        "misses": 0,
                        "partials": 0,
                        "branches": 1,
                        "sessions": 0,
                        "complexity": 0,
                        "complexity_total": 0,
                        "methods": 0,
                    },
                    "removed_diff_coverage": None,
                    "added_diff_coverage": [],
                    "unexpected_line_changes": [
                        [[1, None], [1, "h"]],
                        [[2, None], [2, "h"]],
                    ],
                },
                {
                    "base_name": "Loading/ui.model.ts",
                    "head_name": "Loading/data.qa.ts",
                    "file_was_added_by_diff": False,
                    "file_was_removed_by_diff": False,
                    "base_coverage": None,
                    "head_coverage": {
                        "hits": 3,
                        "misses": 0,
                        "partials": 0,
                        "branches": 1,
                        "sessions": 0,
                        "complexity": 0,
                        "complexity_total": 0,
                        "methods": 0,
                    },
                    "removed_diff_coverage": None,
                    "added_diff_coverage": [],
                    "unexpected_line_changes": [
                        [[1, None], [1, "h"]],
                        [[2, None], [2, "h"]],
                        [[3, None], [3, "h"]],
                    ],
                },
                {
                    "base_name": "Complete/data.qa.ts",
                    "head_name": "Complete/data.qa.ts",
                    "file_was_added_by_diff": True,
                    "file_was_removed_by_diff": False,
                    "base_coverage": None,
                    "head_coverage": {
                        "hits": 4,
                        "misses": 0,
                        "partials": 0,
                        "branches": 1,
                        "sessions": 0,
                        "complexity": 0,
                        "complexity_total": 0,
                        "methods": 0,
                    },
                    "removed_diff_coverage": None,
                    "added_diff_coverage": [[1, "h"], [2, "h"], [3, "h"], [4, "h"]],
                    "unexpected_line_changes": [],
                },
                {
                    "base_name": "src/static/images/rewards/coin-drop.svg",
                    "head_name": "src/static/images/rewards/coin-drop.svg",
                    "file_was_added_by_diff": True,
                    "file_was_removed_by_diff": False,
                    "base_coverage": None,
                    "head_coverage": {
                        "hits": 1,
                        "misses": 0,
                        "partials": 0,
                        "branches": 0,
                        "sessions": 0,
                        "complexity": 0,
                        "complexity_total": 0,
                        "methods": 0,
                    },
                    "removed_diff_coverage": None,
                    "added_diff_coverage": [],
                    "unexpected_line_changes": [],
                },
                {
                    "base_name": "src/product/Rewards/pages/Splash/index.tsx",
                    "head_name": "src/product/Rewards/pages/Splash/index.tsx",
                    "file_was_added_by_diff": False,
                    "file_was_removed_by_diff": False,
                    "base_coverage": {
                        "hits": 35,
                        "misses": 14,
                        "partials": 0,
                        "branches": 9,
                        "sessions": 0,
                        "complexity": 0,
                        "complexity_total": 0,
                        "methods": 7,
                    },
                    "head_coverage": {
                        "hits": 35,
                        "misses": 14,
                        "partials": 0,
                        "branches": 9,
                        "sessions": 0,
                        "complexity": 0,
                        "complexity_total": 0,
                        "methods": 7,
                    },
                    "removed_diff_coverage": [[66, "m"]],
                    "added_diff_coverage": [[66, "m"]],
                    "unexpected_line_changes": [],
                },
                {
                    "base_name": "Loading/index.tsx",
                    "head_name": "Loading/index.tsx",
                    "file_was_added_by_diff": False,
                    "file_was_removed_by_diff": False,
                    "base_coverage": {
                        "hits": 49,
                        "misses": 0,
                        "partials": 0,
                        "branches": 4,
                        "sessions": 0,
                        "complexity": 0,
                        "complexity_total": 0,
                        "methods": 10,
                    },
                    "head_coverage": {
                        "hits": 49,
                        "misses": 0,
                        "partials": 0,
                        "branches": 4,
                        "sessions": 0,
                        "complexity": 0,
                        "complexity_total": 0,
                        "methods": 10,
                    },
                    "removed_diff_coverage": [[17, "h"]],
                    "added_diff_coverage": [[17, "h"]],
                    "unexpected_line_changes": [],
                },
                {
                    "base_name": "Complete/index.tsx",
                    "head_name": "Complete/index.tsx",
                    "file_was_added_by_diff": False,
                    "file_was_removed_by_diff": False,
                    "base_coverage": None,
                    "head_coverage": {
                        "hits": 25,
                        "misses": 0,
                        "partials": 0,
                        "branches": 2,
                        "sessions": 0,
                        "complexity": 0,
                        "complexity_total": 0,
                        "methods": 4,
                    },
                    "removed_diff_coverage": None,
                    "added_diff_coverage": [
                        [2, "h"],
                        [3, "h"],
                        [4, "h"],
                        [6, "h"],
                        [7, "h"],
                        [9, "h"],
                        [11, "h"],
                        [14, "h"],
                        [17, "h"],
                        [18, "h"],
                        [36, "h"],
                        [37, "h"],
                        [41, "h"],
                        [46, "h"],
                    ],
                    "unexpected_line_changes": [
                        [[1, None], [1, "h"]],
                        [[4, None], [8, "h"]],
                        [[6, None], [13, "h"]],
                        [[9, None], [16, "h"]],
                        [[11, None], [20, "h"]],
                        [[12, None], [21, "h"]],
                        [[13, None], [22, "h"]],
                        [[19, None], [29, "h"]],
                        [[20, None], [30, "h"]],
                        [[25, None], [35, "h"]],
                        [[30, None], [48, "h"]],
                    ],
                },
            ],
            "changes_summary": {
                "patch_totals": {
                    "hits": 20,
                    "misses": 1,
                    "partials": 0,
                    "coverage": 0.95238096,
                }
            },
        }
    )
    expected_res = [
        "Complete/index.tsx",
        "Loading/data.qa.ts",
        "ProgressBar/data.qa.ts",
    ]
    assert sorted(x.path for x in res) == expected_res


def test_get_changes_from_comparison_same_line_type():
    res = _get_changes_from_comparison(
        {
            "files": [
                {
                    "base_name": "base_name.ts",
                    "head_name": "head_name.ts",
                    "file_was_added_by_diff": False,
                    "file_was_removed_by_diff": False,
                    "base_coverage": None,
                    "head_coverage": {
                        "hits": 2,
                        "misses": 0,
                        "partials": 0,
                        "branches": 1,
                        "sessions": 0,
                        "complexity": 0,
                        "complexity_total": 0,
                        "methods": 0,
                    },
                    "removed_diff_coverage": [[8, "h"]],
                    "added_diff_coverage": [[8, "h"]],
                    "unexpected_line_changes": [
                        [[1, "p"], [1, "p"]],
                        [[2, "p"], [2, "p"]],
                    ],
                }
            ],
            "changes_summary": {
                "patch_totals": {
                    "hits": 20,
                    "misses": 1,
                    "partials": 0,
                    "coverage": 0.95238096,
                }
            },
        }
    )
    assert res == []


class TestRustifyDiff(object):
    def test_rustify_diff_empty(self):
        assert rustify_diff({}) == {}
        assert rustify_diff(None) == {}

    def test_rustify_simple(self):
        d = {
            "files": {
                "file_1.go": {
                    "type": "modified",
                    "segments": [{"header": list("1313"), "lines": list("---+++ ")}],
                },
                "location/file_1.py": {
                    "type": "modified",
                    "segments": [
                        {
                            "header": ["100", "3", "100", "3"],
                            "lines": ["-lost", "+g", "-sdasdas", "+weq", "-dasda", "+"],
                        }
                    ],
                },
                "deleted.py": {"type": "deleted"},
                "renamed.py": {"type": "modified", "before": "old_renamed.py"},
            }
        }
        expected_res = {
            "deleted.py": ("deleted", None, []),
            "file_1.go": (
                "modified",
                None,
                [((1, 3, 1, 3), ["-", "-", "-", "+", "+", "+", " "])],
            ),
            "location/file_1.py": (
                "modified",
                None,
                [((100, 3, 100, 3), ["-", "+", "-", "+", "-", "+"])],
            ),
            "renamed.py": ("modified", "old_renamed.py", []),
        }
        assert rustify_diff(d) == expected_res

    def test_rustify_diff_new_file(self):
        user_input = {
            "files": {
                "a.txt": {
                    "type": "new",
                    "before": None,
                    "segments": [{"header": ["0", "0", "1", ""], "lines": ["+banana"]}],
                    "stats": {"added": 1, "removed": 0},
                },
                "wildwest/strings.py": {
                    "type": "modified",
                    "before": None,
                    "segments": [
                        {
                            "header": ["43", "7", "43", "7"],
                            "lines": [
                                "     if len(this_string) == 20:",
                                "         return True",
                                "     if len(set(this_string)) == 7:",
                                '-        print("0043")',
                                '+        print("0044")',
                                '         # k = b"Prè áaaaì u aáa. Ponto, dois-pontos e travessão são exemplos de sinais de pontuação que utilizamos"',
                                "         return True",
                                "     return False",
                            ],
                        }
                    ],
                    "stats": {"added": 1, "removed": 1},
                },
            }
        }
        expected_result = {
            "a.txt": ("new", None, [((0, 0, 1, 0), ["+"])]),
            "wildwest/strings.py": (
                "modified",
                None,
                [((43, 7, 43, 7), [" ", " ", " ", "-", "+", " ", " ", " "])],
            ),
        }
        assert rustify_diff(user_input) == expected_result
