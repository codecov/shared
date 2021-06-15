import pytest
from shared.validation.experimental import validate_experimental
from shared.validation.exceptions import InvalidYamlException


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


def test_validation_with_null_on_status():
    user_input = {
        "coverage": {"status": {"project": {"default": None}, "patch": False}},
        "ignore": ["coffee", "test"],
    }
    expected_result = {
        "coverage": {"status": {"project": {"default": None}, "patch": False}},
        "ignore": ["^coffee.*", "^test.*"],
    }
    res = validate_experimental(user_input, show_secret=False)
    assert res == expected_result


def test_improper_layout():
    user_input = {
        "coverage": {"status": {"project": {"default": None}, "patch": False}},
        "comment": {"layout": "banana,apple"},
    }
    with pytest.raises(InvalidYamlException) as exc:
        validate_experimental(user_input, show_secret=False)
    assert exc.value.error_location == {
        "comment": [{"layout": ["Unexpected values on layout: apple,banana"]}]
    }


def test_proper_layout():
    user_input = {
        "coverage": {"status": {"project": {"default": None}, "patch": False}},
        "comment": {"layout": "files:10,footer"},
    }
    res = validate_experimental(user_input, show_secret=False)
    assert res == {
        "coverage": {"status": {"project": {"default": None}, "patch": False}},
        "comment": {"layout": "files:10,footer"},
    }


def test_codecov_branch():
    user_input = {
        "codecov": {"branch": "origin/pterosaur"},
    }
    res = validate_experimental(user_input, show_secret=False)
    assert res == {
        "codecov": {"branch": "pterosaur"},
    }
