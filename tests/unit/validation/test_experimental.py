from shared.validation.experimental import validate_experimental


def test_validation_with_branches():
    user_input = {
        "comment": {
            "require_head": True,
            "require_base": True,
            "layout": "diff",
            "require_changes": True,
            "branches": ["master"],
            "behavior": "once",
            "after_n_builds": 6,
        },
        "coverage": {
            "status": {"project": {"default": {"threshold": "1%"}}, "patch": False}
        },
        "github_checks": {"annotations": False},
        "fixes": [
            "/opt/conda/lib/python3.8/site-packages/::project/",
            "C:/Users/circleci/project/build/win_tmp/build/::project/",
        ],
        "ignore": ["coffee", "party_man", "test"],
        "codecov": {"notify": {"after_n_builds": 6}},
    }
    expected_result = {
        "comment": {
            "require_head": True,
            "require_base": True,
            "layout": "diff",
            "require_changes": True,
            "branches": ["^master$"],
            "behavior": "once",
            "after_n_builds": 6,
        },
        "coverage": {
            "status": {"project": {"default": {"threshold": 1}}, "patch": False}
        },
        "github_checks": {"annotations": False},
        "fixes": [
            "^/opt/conda/lib/python3.8/site-packages/::project/",
            "^C:/Users/circleci/project/build/win_tmp/build/::project/",
        ],
        "ignore": ["^coffee.*", "^party_man.*", "^test.*"],
        "codecov": {"notify": {"after_n_builds": 6}},
    }
    res = validate_experimental(user_input, show_secret=False)
    assert res == expected_result


def test_validation_with_null_on_paths():
    user_input = {
        "comment": {"require_head": True, "behavior": "once", "after_n_builds": 6,},
        "coverage": {
            "status": {"project": {"default": {"threshold": "1%"}}, "patch": False},
            "notify": {"slack": {"default": {"paths": None}}},
        },
        "ignore": ["coffee", "test"],
    }
    expected_result = {
        "comment": {"require_head": True, "behavior": "once", "after_n_builds": 6},
        "coverage": {
            "status": {"project": {"default": {"threshold": 1.0}}, "patch": False},
            "notify": {"slack": {"default": {"paths": None}}},
        },
        "ignore": ["^coffee.*", "^test.*"],
    }
    res = validate_experimental(user_input, show_secret=False)
    assert res == expected_result
