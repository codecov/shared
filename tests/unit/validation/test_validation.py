import os

import pytest

from shared.config import ConfigHelper, get_config
from shared.validation.exceptions import InvalidYamlException
from shared.yaml.validation import (
    _calculate_error_location_and_message_from_error_dict,
    do_actual_validation,
    validate_yaml,
)
from tests.base import BaseTestCase


class TestUserYamlValidation(BaseTestCase):
    def test_empty_case(self):
        user_input = {}
        expected_result = {}
        assert validate_yaml(user_input) == expected_result

    @pytest.mark.parametrize("input_value", ["", 10, [], tuple(), set()])
    def test_wrong_object_type(self, input_value):
        with pytest.raises(InvalidYamlException) as exc:
            validate_yaml(input_value)
        exception = exc.value
        assert exception.error_location == []
        assert exception.error_message == "Yaml needs to be a dict"
        assert exception.original_exc is None

    @pytest.mark.parametrize(
        "user_input, expected_result",
        [
            (
                {
                    "coverage": {"status": {"patch": True, "project": False}},
                    "comment": False,
                },
                {
                    "comment": False,
                    "coverage": {"status": {"patch": True, "project": False}},
                },
            ),
            (
                {
                    "codecov": {"bot": "codecov-io", "require_ci_to_pass": False},
                    "coverage": {
                        "status": {
                            "project": {
                                "default": {"target": "78%", "threshold": "5%"}
                            },
                            "patch": {"default": {"target": "75%"}},
                        }
                    },
                },
                {
                    "codecov": {"bot": "codecov-io", "require_ci_to_pass": False},
                    "coverage": {
                        "status": {
                            "project": {"default": {"target": 78.0, "threshold": 5.0}},
                            "patch": {"default": {"target": 75.0}},
                        }
                    },
                },
            ),
            (
                {
                    "coverage": {
                        "status": {
                            "project": False,
                            "patch": {
                                "default": {"informational": True},
                                "ui": {"informational": True},
                            },
                            "changes": False,
                        }
                    },
                    "comment": False,
                    "flags": {"ui": {"paths": ["/ui-v2/"]}},
                    "github_checks": {"annotations": False},
                    "ignore": [
                        "agent/uiserver/bindata_assetfs.go",
                        "vendor/**/*",
                        "**/*.pb.go",
                    ],
                },
                {
                    "coverage": {
                        "status": {
                            "project": False,
                            "patch": {
                                "default": {"informational": True},
                                "ui": {"informational": True},
                            },
                            "changes": False,
                        }
                    },
                    "comment": False,
                    "flags": {"ui": {"paths": ["^/ui-v2/.*"]}},
                    "github_checks": {"annotations": False},
                    "ignore": [
                        "^agent/uiserver/bindata_assetfs.go.*",
                        "(?s:vendor/.*/[^\\/]*)\\Z",
                        "(?s:.*/[^\\/]*\\.pb\\.go.*)\\Z",
                    ],
                },
            ),
            (
                {
                    "comment": {
                        "require_head": True,
                        "require_base": True,
                        "layout": "diff",
                        "require_changes": True,
                        "branches": ["master"],
                        "behavior": "once",
                        "after_n_builds": 6,
                        "hide_project_coverage": True,
                    },
                    "coverage": {
                        "status": {
                            "project": {"default": {"threshold": "1%"}},
                            "patch": False,
                        }
                    },
                    "github_checks": {"annotations": False},
                    "fixes": [
                        "/opt/conda/lib/python3.8/site-packages/::project/",
                        "C:/Users/circleci/project/build/win_tmp/build/::project/",
                    ],
                    "ignore": ["coffee", "party_man", "test"],
                    "codecov": {"notify": {"after_n_builds": 6}},
                },
                {
                    "comment": {
                        "require_head": True,
                        "require_base": True,
                        "layout": "diff",
                        "require_changes": True,
                        "branches": ["^master$"],
                        "behavior": "once",
                        "after_n_builds": 6,
                        "hide_project_coverage": True,
                    },
                    "coverage": {
                        "status": {
                            "project": {"default": {"threshold": 1}},
                            "patch": False,
                        }
                    },
                    "github_checks": {"annotations": False},
                    "fixes": [
                        "^/opt/conda/lib/python3.8/site-packages/::project/",
                        "^C:/Users/circleci/project/build/win_tmp/build/::project/",
                    ],
                    "ignore": ["^coffee.*", "^party_man.*", "^test.*"],
                    "codecov": {"notify": {"after_n_builds": 6}},
                },
            ),
            (
                {
                    "ignore": ["js/plugins", "plugins"],
                    "coverage": {
                        "notify": {
                            "slack": {
                                "default": {
                                    "url": "https://hooks.slack.com/services/testdazzd/testrf4k6py/test72nq0j0ke3prs2fdvfuj",
                                    "only_pulls": False,
                                    "branches": ["master", "qa", "dev"],
                                }
                            }
                        }
                    },
                },
                {
                    "ignore": ["^js/plugins.*", "^plugins.*"],
                    "coverage": {
                        "notify": {
                            "slack": {
                                "default": {
                                    "url": "https://hooks.slack.com/services/testdazzd/testrf4k6py/test72nq0j0ke3prs2fdvfuj",
                                    "only_pulls": False,
                                    "branches": ["^master$", "^qa$", "^dev$"],
                                }
                            }
                        }
                    },
                },
            ),
            (
                {
                    "codecov": {"notify": {"manual_trigger": True}},
                },
                {
                    "codecov": {"notify": {"manual_trigger": True}},
                },
            ),
        ],
    )
    def test_random_real_life_cases(self, user_input, expected_result):
        # Some random cases based on real world examples
        assert expected_result == validate_yaml(user_input)

    def test_case_with_experimental_turned_on_valid(self, mocker):
        mocker.patch.dict(os.environ, {"CERBERUS_VALIDATOR_RATE": "1.0"})
        user_input = {"coverage": {"status": {"patch": True}}}
        expected_result = {"coverage": {"status": {"patch": True}}}
        assert expected_result == validate_yaml(user_input)

    def test_case_with_experimental_turned_invalid(self, mocker):
        mocker.patch.dict(os.environ, {"CERBERUS_VALIDATOR_RATE": "1.0"})
        user_input = {"coverage": {"status": {"patch": "banana"}}}
        with pytest.raises(InvalidYamlException) as ex:
            validate_yaml(user_input)
        assert ex.value.error_location == ["coverage", "status", "patch"]
        assert ex.value.error_message == "must be of ['dict', 'boolean'] type"

    def test_many_flags_validation(self):
        user_input = {
            "codecov": {"max_report_age": False, "notify": {"after_n_builds": 10}},
            "comment": {"layout": "reach,footer"},
            "coverage": {
                "status": {
                    "patch": {
                        "default": True,
                        "numbers_only": {"paths": ["wildwest/numbers.py"]},
                        "strings_only": {"paths": ["wildwest/strings.py"]},
                        "one": {"flags": ["one"]},
                        "two": {"flags": ["two"]},
                        "three": {"flags": ["three"]},
                        "four": {"flags": ["four"]},
                        "five": {"flags": ["five"]},
                        "six": {"flags": ["six"]},
                        "seven": {"flags": ["seven"]},
                        "eight": {"flags": ["eight"]},
                        "nine": {"flags": ["nine"]},
                        "ten": {"flags": ["ten"]},
                        "eleven": {"flags": ["eleven"]},
                        "one_without_t": {"flags": ["one"], "paths": ["wildwest"]},
                        "two_without_t": {"flags": ["two"], "paths": ["wildwest"]},
                        "three_without_t": {"flags": ["three"], "paths": ["wildwest"]},
                        "four_without_t": {"flags": ["four"], "paths": ["wildwest"]},
                        "five_without_t": {"flags": ["five"], "paths": ["wildwest"]},
                        "six_without_t": {"flags": ["six"], "paths": ["wildwest"]},
                        "seven_without_t": {"flags": ["seven"], "paths": ["wildwest"]},
                        "eight_without_t": {"flags": ["eight"], "paths": ["wildwest"]},
                        "nine_without_t": {"flags": ["nine"], "paths": ["wildwest"]},
                        "ten_without_t": {"flags": ["ten"], "paths": ["wildwest"]},
                        "eleven_without_t": {
                            "flags": ["eleven"],
                            "paths": ["wildwest"],
                        },
                    },
                    "project": {
                        "default": True,
                        "numbers_only": {"paths": ["wildwest/numbers.py"]},
                        "strings_only": {"paths": ["wildwest/strings.py"]},
                        "one": {"flags": ["one"]},
                        "two": {"flags": ["two"]},
                        "three": {"flags": ["three"]},
                        "four": {"flags": ["four"]},
                        "five": {"flags": ["five"]},
                        "six": {"flags": ["six"]},
                        "seven": {"flags": ["seven"]},
                        "eight": {"flags": ["eight"]},
                        "nine": {"flags": ["nine"]},
                        "ten": {"flags": ["ten"]},
                        "eleven": {"flags": ["eleven"]},
                        "one_without_t": {"flags": ["one"], "paths": ["wildwest"]},
                        "two_without_t": {"flags": ["two"], "paths": ["wildwest"]},
                        "three_without_t": {"flags": ["three"], "paths": ["wildwest"]},
                        "four_without_t": {"flags": ["four"], "paths": ["wildwest"]},
                        "five_without_t": {"flags": ["five"], "paths": ["wildwest"]},
                        "six_without_t": {"flags": ["six"], "paths": ["wildwest"]},
                        "seven_without_t": {"flags": ["seven"], "paths": ["wildwest"]},
                        "eight_without_t": {"flags": ["eight"], "paths": ["wildwest"]},
                        "nine_without_t": {"flags": ["nine"], "paths": ["wildwest"]},
                        "ten_without_t": {"flags": ["ten"], "paths": ["wildwest"]},
                        "eleven_without_t": {
                            "flags": ["eleven"],
                            "paths": ["wildwest"],
                        },
                    },
                    "changes": {
                        "numbers_only": {"paths": ["wildwest/numbers.py"]},
                        "strings_only": {"paths": ["wildwest/strings.py"]},
                        "default": True,
                        "one": {"flags": ["one"]},
                        "two": {"flags": ["two"]},
                        "three": {"flags": ["three"]},
                        "four": {"flags": ["four"]},
                        "five": {"flags": ["five"]},
                        "six": {"flags": ["six"]},
                        "seven": {"flags": ["seven"]},
                        "eight": {"flags": ["eight"]},
                        "nine": {"flags": ["nine"]},
                        "ten": {"flags": ["ten"]},
                        "eleven": {"flags": ["eleven"]},
                        "one_without_t": {"flags": ["one"], "paths": ["wildwest"]},
                        "two_without_t": {"flags": ["two"], "paths": ["wildwest"]},
                        "three_without_t": {"flags": ["three"], "paths": ["wildwest"]},
                        "four_without_t": {"flags": ["four"], "paths": ["wildwest"]},
                        "five_without_t": {"flags": ["five"], "paths": ["wildwest"]},
                        "six_without_t": {"flags": ["six"], "paths": ["wildwest"]},
                        "seven_without_t": {"flags": ["seven"], "paths": ["wildwest"]},
                        "eight_without_t": {"flags": ["eight"], "paths": ["wildwest"]},
                        "nine_without_t": {"flags": ["nine"], "paths": ["wildwest"]},
                        "ten_without_t": {"flags": ["ten"], "paths": ["wildwest"]},
                        "eleven_without_t": {
                            "flags": ["eleven"],
                            "paths": ["wildwest"],
                        },
                    },
                }
            },
            "flag_management": {
                "default_rules": {
                    "carryforward": False,
                    "statuses": [{"name_prefix": "aaa", "type": "patch"}],
                },
                "individual_flags": [
                    {"name": "cawcaw", "paths": ["banana"], "after_n_builds": 3}
                ],
            },
        }
        expected_result = {
            "codecov": {"max_report_age": False, "notify": {"after_n_builds": 10}},
            "comment": {"layout": "reach,footer"},
            "coverage": {
                "status": {
                    "patch": {
                        "default": True,
                        "numbers_only": {"paths": ["^wildwest/numbers.py.*"]},
                        "strings_only": {"paths": ["^wildwest/strings.py.*"]},
                        "one": {"flags": ["one"]},
                        "two": {"flags": ["two"]},
                        "three": {"flags": ["three"]},
                        "four": {"flags": ["four"]},
                        "five": {"flags": ["five"]},
                        "six": {"flags": ["six"]},
                        "seven": {"flags": ["seven"]},
                        "eight": {"flags": ["eight"]},
                        "nine": {"flags": ["nine"]},
                        "ten": {"flags": ["ten"]},
                        "eleven": {"flags": ["eleven"]},
                        "one_without_t": {"flags": ["one"], "paths": ["^wildwest.*"]},
                        "two_without_t": {"flags": ["two"], "paths": ["^wildwest.*"]},
                        "three_without_t": {
                            "flags": ["three"],
                            "paths": ["^wildwest.*"],
                        },
                        "four_without_t": {"flags": ["four"], "paths": ["^wildwest.*"]},
                        "five_without_t": {"flags": ["five"], "paths": ["^wildwest.*"]},
                        "six_without_t": {"flags": ["six"], "paths": ["^wildwest.*"]},
                        "seven_without_t": {
                            "flags": ["seven"],
                            "paths": ["^wildwest.*"],
                        },
                        "eight_without_t": {
                            "flags": ["eight"],
                            "paths": ["^wildwest.*"],
                        },
                        "nine_without_t": {"flags": ["nine"], "paths": ["^wildwest.*"]},
                        "ten_without_t": {"flags": ["ten"], "paths": ["^wildwest.*"]},
                        "eleven_without_t": {
                            "flags": ["eleven"],
                            "paths": ["^wildwest.*"],
                        },
                    },
                    "project": {
                        "default": True,
                        "numbers_only": {"paths": ["^wildwest/numbers.py.*"]},
                        "strings_only": {"paths": ["^wildwest/strings.py.*"]},
                        "one": {"flags": ["one"]},
                        "two": {"flags": ["two"]},
                        "three": {"flags": ["three"]},
                        "four": {"flags": ["four"]},
                        "five": {"flags": ["five"]},
                        "six": {"flags": ["six"]},
                        "seven": {"flags": ["seven"]},
                        "eight": {"flags": ["eight"]},
                        "nine": {"flags": ["nine"]},
                        "ten": {"flags": ["ten"]},
                        "eleven": {"flags": ["eleven"]},
                        "one_without_t": {"flags": ["one"], "paths": ["^wildwest.*"]},
                        "two_without_t": {"flags": ["two"], "paths": ["^wildwest.*"]},
                        "three_without_t": {
                            "flags": ["three"],
                            "paths": ["^wildwest.*"],
                        },
                        "four_without_t": {"flags": ["four"], "paths": ["^wildwest.*"]},
                        "five_without_t": {"flags": ["five"], "paths": ["^wildwest.*"]},
                        "six_without_t": {"flags": ["six"], "paths": ["^wildwest.*"]},
                        "seven_without_t": {
                            "flags": ["seven"],
                            "paths": ["^wildwest.*"],
                        },
                        "eight_without_t": {
                            "flags": ["eight"],
                            "paths": ["^wildwest.*"],
                        },
                        "nine_without_t": {"flags": ["nine"], "paths": ["^wildwest.*"]},
                        "ten_without_t": {"flags": ["ten"], "paths": ["^wildwest.*"]},
                        "eleven_without_t": {
                            "flags": ["eleven"],
                            "paths": ["^wildwest.*"],
                        },
                    },
                    "changes": {
                        "numbers_only": {"paths": ["^wildwest/numbers.py.*"]},
                        "strings_only": {"paths": ["^wildwest/strings.py.*"]},
                        "default": True,
                        "one": {"flags": ["one"]},
                        "two": {"flags": ["two"]},
                        "three": {"flags": ["three"]},
                        "four": {"flags": ["four"]},
                        "five": {"flags": ["five"]},
                        "six": {"flags": ["six"]},
                        "seven": {"flags": ["seven"]},
                        "eight": {"flags": ["eight"]},
                        "nine": {"flags": ["nine"]},
                        "ten": {"flags": ["ten"]},
                        "eleven": {"flags": ["eleven"]},
                        "one_without_t": {"flags": ["one"], "paths": ["^wildwest.*"]},
                        "two_without_t": {"flags": ["two"], "paths": ["^wildwest.*"]},
                        "three_without_t": {
                            "flags": ["three"],
                            "paths": ["^wildwest.*"],
                        },
                        "four_without_t": {"flags": ["four"], "paths": ["^wildwest.*"]},
                        "five_without_t": {"flags": ["five"], "paths": ["^wildwest.*"]},
                        "six_without_t": {"flags": ["six"], "paths": ["^wildwest.*"]},
                        "seven_without_t": {
                            "flags": ["seven"],
                            "paths": ["^wildwest.*"],
                        },
                        "eight_without_t": {
                            "flags": ["eight"],
                            "paths": ["^wildwest.*"],
                        },
                        "nine_without_t": {"flags": ["nine"], "paths": ["^wildwest.*"]},
                        "ten_without_t": {"flags": ["ten"], "paths": ["^wildwest.*"]},
                        "eleven_without_t": {
                            "flags": ["eleven"],
                            "paths": ["^wildwest.*"],
                        },
                    },
                }
            },
            "flag_management": {
                "default_rules": {
                    "carryforward": False,
                    "statuses": [{"name_prefix": "aaa", "type": "patch"}],
                },
                "individual_flags": [
                    {"name": "cawcaw", "paths": ["^banana.*"], "after_n_builds": 3}
                ],
            },
        }
        assert validate_yaml(user_input) == expected_result

    def test_validate_bot_none(self):
        user_input = {"codecov": {"bot": None}}
        expected_result = {"codecov": {"bot": None}}
        result = validate_yaml(user_input)
        assert result == expected_result

    def test_validate_flag_too_long(self):
        user_input = {"flags": {"abcdefg" * 7: {"paths": ["banana"]}}}
        with pytest.raises(InvalidYamlException) as exc:
            validate_yaml(user_input)
        assert exc.value.error_location == [
            "flags",
            "abcdefgabcdefgabcdefgabcdefgabcdefgabcdefgabcdefg",
        ]

    def test_validate_parser_only_field(self):
        user_input = {"parsers": {"go": {"partials_as_hits": True}}}
        expected_result = {"parsers": {"go": {"partials_as_hits": True}}}
        result = validate_yaml(user_input)
        assert result == expected_result

    def test_simple_case(self):
        encoded_value = "secret:v1::zsV9A8pHadNle357DGJHbZCTyCYA+TXdUd9TN3IY2DIWcPOtgK3Pg1EgA6OZr9XJ1EsdpL765yWrN4pfR3elRdN2LUwiuv6RkNjpbiruHx45agsgxdu8fi24p5pkCLvjcW0HqdH2PTvmHauIp+ptgA=="
        user_input = {
            "coverage": {
                "precision": 2,
                "round": "down",
                "range": "70...100",
                "status": {
                    "project": {
                        "custom_project": {
                            "carryforward_behavior": "exclude",
                            "flag_coverage_not_uploaded_behavior": "exclude",
                        }
                    },
                    "patch": True,
                    "changes": False,
                    "default_rules": {
                        "carryforward_behavior": "pass",
                        "flag_coverage_not_uploaded_behavior": "pass",
                    },
                    "no_upload_behavior": "pass",
                },
                "notify": {"irc": {"user_given_title": {"password": encoded_value}}},
            },
            "codecov": {"notify": {"require_ci_to_pass": True}},
            "comment": {
                "behavior": "default",
                "layout": "header, diff",
                "require_changes": False,
                "show_carryforward_flags": False,
            },
            "parsers": {
                "gcov": {
                    "branch_detection": {
                        "conditional": True,
                        "loop": True,
                        "macro": False,
                        "method": False,
                    }
                },
                "jacoco": {"partials_as_hits": True},
            },
            "cli": {
                "plugins": {"pycoverage": {"report_type": "json"}},
            },
        }
        expected_result = {
            "coverage": {
                "precision": 2,
                "round": "down",
                "range": [70, 100],
                "status": {
                    "project": {
                        "custom_project": {
                            "carryforward_behavior": "exclude",
                            "flag_coverage_not_uploaded_behavior": "exclude",
                        }
                    },
                    "patch": True,
                    "changes": False,
                    "default_rules": {
                        "carryforward_behavior": "pass",
                        "flag_coverage_not_uploaded_behavior": "pass",
                    },
                    "no_upload_behavior": "pass",
                },
                "notify": {"irc": {"user_given_title": {"password": encoded_value}}},
            },
            "codecov": {"notify": {}, "require_ci_to_pass": True},
            "comment": {
                "behavior": "default",
                "layout": "header, diff",
                "require_changes": False,
                "show_carryforward_flags": False,
            },
            "parsers": {
                "gcov": {
                    "branch_detection": {
                        "conditional": True,
                        "loop": True,
                        "macro": False,
                        "method": False,
                    }
                },
                "jacoco": {"partials_as_hits": True},
            },
            "cli": {
                "plugins": {"pycoverage": {"report_type": "json"}},
            },
        }
        assert validate_yaml(user_input) == expected_result

    def test_negative_notify_after_n_builds(self):
        user_input = {"codecov": {"notify": {"after_n_builds": -1}}}
        with pytest.raises(InvalidYamlException) as exc:
            validate_yaml(user_input)
        exception = exc.value
        assert exc.value.error_location == ["codecov", "notify", "after_n_builds"]
        assert exc.value.error_message == "min value is 0"

    def test_positive_notify_after_n_builds(self):
        user_input = {"codecov": {"notify": {"after_n_builds": 1}}}
        res = validate_yaml(user_input)
        assert res == {"codecov": {"notify": {"after_n_builds": 1}}}

    def test_negative_comments_after_n_builds(self):
        user_input = {"comment": {"after_n_builds": -1}}
        with pytest.raises(InvalidYamlException) as exc:
            validate_yaml(user_input)
        exception = exc.value
        assert exc.value.error_location == ["comment", "after_n_builds"]
        assert exc.value.error_message == "min value is 0"

    def test_invalid_yaml_case(self):
        user_input = {
            "coverage": {
                "round": "down",
                "precision": 2,
                "range": "70...100",
                "status": {"project": {"base": "auto", "aa": True}},
            },
            "ignore": ["Pods/.*"],
        }
        with pytest.raises(InvalidYamlException) as exc:
            validate_yaml(user_input)
        assert exc.value.error_location == ["coverage", "status", "project", "base"]
        assert exc.value.error_message == "must be of ['dict', 'boolean'] type"

    def test_invalid_yaml_case_custom_validator(self):
        user_input = {
            "coverage": {
                "round": "down",
                "precision": 2,
                "range": "70...5000",
                "status": {"project": {"percent": "abc"}},
            },
            "ignore": ["Pods/.*"],
        }
        with pytest.raises(InvalidYamlException) as exc:
            validate_yaml(user_input)
        assert exc.value.error_location == ["coverage", "range"]
        assert exc.value.error_message == "must be of list type"

    def test_invalid_yaml_case_no_upload_behavior(self):
        user_input = {
            "coverage": {
                "round": "down",
                "precision": 2,
                "range": "70...100",
                "status": {
                    "project": {"percent": "abc"},
                    "no_upload_behavior": "no-pass",
                },
            },
            "ignore": ["Pods/.*"],
        }
        with pytest.raises(InvalidYamlException) as exc:
            validate_yaml(user_input)
        assert exc.value.error_location == ["coverage", "status", "no_upload_behavior"]
        assert exc.value.error_message == "unallowed value no-pass"

    def test_yaml_with_null_threshold(self):
        user_input = {
            "codecov": {"notify": {}, "require_ci_to_pass": True},
            "comment": {
                "behavior": "default",
                "branches": None,
                "layout": "reach, diff, flags, files",
                "require_base": False,
                "require_changes": False,
                "require_head": False,
            },
            "coverage": {
                "precision": 2,
                "range": "50...80",
                "round": "down",
                "status": {
                    "changes": False,
                    "patch": True,
                    "project": {
                        "default": {"target": "auto", "threshold": None, "base": "auto"}
                    },
                },
            },
        }
        res = validate_yaml(user_input)
        expected_result = {
            "codecov": {"notify": {}, "require_ci_to_pass": True},
            "comment": {
                "behavior": "default",
                "branches": None,
                "layout": "reach, diff, flags, files",
                "require_base": False,
                "require_changes": False,
                "require_head": False,
            },
            "coverage": {
                "precision": 2,
                "range": [50.0, 80.0],
                "round": "down",
                "status": {
                    "changes": False,
                    "patch": True,
                    "project": {
                        "default": {"target": "auto", "threshold": None, "base": "auto"}
                    },
                },
            },
        }
        assert res == expected_result

    def test_yaml_with_status_case(self):
        user_input = {
            "coverage": {
                "round": "down",
                "precision": 2,
                "range": "70...100",
                "status": {"project": {"default": {"base": "auto"}}},
            },
            "ignore": ["Pods/.*"],
        }
        expected_result = {
            "coverage": {
                "round": "down",
                "precision": 2,
                "range": [70.0, 100.0],
                "status": {"project": {"default": {"base": "auto"}}},
            },
            "ignore": ["Pods/.*"],
        }
        result = validate_yaml(user_input)
        assert result == expected_result

    def test_yaml_with_flag_management(self):
        user_input = {
            "flag_management": {
                "default_rules": {
                    "carryforward": True,
                    "statuses": [
                        {
                            "type": "project",
                            "name_prefix": "healthcare",
                            "threshold": 80,
                        }
                    ],
                },
                "individual_flags": [
                    {
                        "name": "flag_banana",
                        "statuses": [
                            {
                                "type": "patch",
                                "name_prefix": "alliance",
                                "flag_coverage_not_uploaded_behavior": "include",
                            }
                        ],
                    }
                ],
            }
        }
        expected_result = {
            "flag_management": {
                "individual_flags": [
                    {
                        "name": "flag_banana",
                        "statuses": [
                            {
                                "type": "patch",
                                "name_prefix": "alliance",
                                "flag_coverage_not_uploaded_behavior": "include",
                            }
                        ],
                    }
                ],
                "default_rules": {
                    "carryforward": True,
                    "statuses": [
                        {
                            "type": "project",
                            "name_prefix": "healthcare",
                            "threshold": 80.0,
                        }
                    ],
                },
            }
        }
        result = validate_yaml(user_input)
        assert result == expected_result

    def test_yaml_with_flag_management_statuses_with_flags(self):
        user_input = {
            "flag_management": {
                "default_rules": {
                    "carryforward": True,
                    "statuses": [
                        {
                            "type": "project",
                            "name_prefix": "healthcare",
                            "threshold": 80,
                            "flags": ["hahaha"],
                        }
                    ],
                },
                "individual_flags": [
                    {
                        "name": "flag_banana",
                        "statuses": [
                            {
                                "type": "patch",
                                "name_prefix": "alliance",
                                "flag_coverage_not_uploaded_behavior": "include",
                            }
                        ],
                    }
                ],
            }
        }
        with pytest.raises(InvalidYamlException) as exc:
            validate_yaml(user_input)
            assert exc.value.error_location == [
                "flag_management",
                "default_rules",
                "statuses",
                0,
                "flags",
            ]
            assert exc.value.error_message == "extra keys not allowed"

    def test_github_checks(self):
        user_input = {"github_checks": True}
        expected_result = {"github_checks": True}
        assert validate_yaml(user_input) == expected_result
        user_input = {"github_checks": {"annotations": False}}
        expected_result = {"github_checks": {"annotations": False}}
        assert validate_yaml(user_input) == expected_result

    def test_validate_jacoco_partials(self):
        user_input = {"parsers": {"jacoco": {"partials_as_hits": True}}}
        expected_result = {"parsers": {"jacoco": {"partials_as_hits": True}}}
        result = validate_yaml(user_input)
        assert result == expected_result


class TestValidationConfig(object):
    def test_validate_default_config_yaml(self, mocker):
        mocker.patch.dict(os.environ, {}, clear=True)
        mocker.patch.object(
            ConfigHelper, "load_yaml_file", side_effect=FileNotFoundError()
        )
        this_config = ConfigHelper()
        mocker.patch("shared.config._get_config_instance", return_value=this_config)
        expected_result = {
            "codecov": {"require_ci_to_pass": True},
            "coverage": {
                "precision": 2,
                "round": "down",
                "range": [60.0, 80.0],
                "status": {
                    "project": True,
                    "patch": True,
                    "changes": False,
                    "default_rules": {"flag_coverage_not_uploaded_behavior": "include"},
                },
            },
            "comment": {
                "layout": "reach,diff,flags,tree,reach",
                "behavior": "default",
                "show_carryforward_flags": False,
            },
            "github_checks": {"annotations": True},
            "slack_app": True,
        }
        res = validate_yaml(
            get_config("site", default={}),
            show_secrets_for=("github", "11934774", "154468867"),
        )
        assert res == expected_result


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
    res = do_actual_validation(user_input, show_secrets_for=None)
    assert res == expected_result


def test_validation_with_flag_carryforward():
    user_input = {
        "flags": {
            "old-flag": {
                "carryforward": True,
                "carryforward_mode": "labels",
            },
            "other-old-flag": {
                "carryforward": True,
                "carryforward_mode": "all",
            },
        },
        "flag_management": {
            "individual_flags": [
                {"name": "abcdef", "carryforward_mode": "all"},
                {"name": "abcdef", "carryforward_mode": "labels"},
            ]
        },
    }
    assert do_actual_validation(user_input, show_secrets_for=None) == user_input


def test_validation_with_flag_carryforward_invalid_mode():
    user_input = {
        "flag_management": {
            "individual_flags": [
                {"name": "abcdef", "carryforward_mode": "mario"},
                {"name": "abcdef", "carryforward_mode": "labels"},
            ]
        },
    }
    with pytest.raises(InvalidYamlException) as exp:
        do_actual_validation(user_input, show_secrets_for=None)
    assert exp.value.error_dict == {
        "flag_management": [
            {
                "individual_flags": [
                    {0: [{"carryforward_mode": ["unallowed value mario"]}]}
                ]
            }
        ]
    }


def test_validation_with_null_on_paths():
    user_input = {
        "comment": {"require_head": True, "behavior": "once", "after_n_builds": 6},
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
    res = do_actual_validation(user_input, show_secrets_for=None)
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
    res = do_actual_validation(user_input, show_secrets_for=None)
    assert res == expected_result


def test_improper_layout():
    user_input = {
        "coverage": {"status": {"project": {"default": None}, "patch": False}},
        "comment": {"layout": "banana,apple"},
    }
    with pytest.raises(InvalidYamlException) as exc:
        do_actual_validation(user_input, show_secrets_for=None)
    assert exc.value.error_dict == {
        "comment": [{"layout": ["Unexpected values on layout: apple,banana"]}]
    }
    assert exc.value.error_location == ["comment", "layout"]


def test_proper_layout():
    user_input = {
        "coverage": {"status": {"project": {"default": None}, "patch": False}},
        "comment": {"layout": "files:10,footer"},
    }
    res = do_actual_validation(user_input, show_secrets_for=None)
    assert res == {
        "coverage": {"status": {"project": {"default": None}, "patch": False}},
        "comment": {"layout": "files:10,footer"},
    }


def test_codecov_branch():
    user_input = {"codecov": {"branch": "origin/pterosaur"}}
    res = do_actual_validation(user_input, show_secrets_for=None)
    assert res == {"codecov": {"branch": "pterosaur"}}


def test_calculate_error_location_and_message_from_error_dict():
    error_dict = {"comment": [{"layout": {"deep": [[[[[{"inside": [["value"]]}]]]]]}}]}
    assert (
        ["comment", "layout", "deep", "inside"],
        "value",
    ) == _calculate_error_location_and_message_from_error_dict(error_dict)
    # case where the value is just very nested.
    # This is not a requirement of any kind. This is just so
    # there are no cases where a customer can send some special yaml with loops
    # and make us keep parsing this forever
    # It might even be overkill
    assert (
        ["value", "some", "thing"],
        "[[['haha']]]",
    ) == _calculate_error_location_and_message_from_error_dict(
        {"value": {"some": {"thing": [[[[[[[[[[[[[[[[[[[["haha"]]]]]]]]]]]]]]]]]]]]}}}
    )


def test_email_field_with_and_without_secret():
    user_input = {
        "coverage": {
            "notify": {
                "email": {
                    "default": {
                        "to": [
                            "example@domain.com",
                            "secret:v1::hfxSizNpugwZzYZXXRxxlszUetU8tyVG1HXCEdK5qeC9XhtxkCsb/Z5nvp70mp4zlbfcinTy9C9lSGXZAmN8uGKuhWnwrFPfYupe7jQ5KQY=",
                        ],
                        "threshold": "1%",
                        "only_pulls": False,
                        "layout": "reach, diff, flags",
                        "flags": None,
                        "paths": None,
                    }
                }
            }
        }
    }
    assert do_actual_validation(
        user_input, show_secrets_for=("github", "11934774", "154468867")
    ) == {
        "coverage": {
            "notify": {
                "email": {
                    "default": {
                        "to": ["example@domain.com", "secondexample@seconddomain.com"],
                        "threshold": 1.0,
                        "only_pulls": False,
                        "layout": "reach, diff, flags",
                        "flags": None,
                        "paths": None,
                    }
                }
            }
        }
    }
    assert do_actual_validation(user_input, show_secrets_for=None) == {
        "coverage": {
            "notify": {
                "email": {
                    "default": {
                        "to": [
                            "example@domain.com",
                            "secret:v1::hfxSizNpugwZzYZXXRxxlszUetU8tyVG1HXCEdK5qeC9XhtxkCsb/Z5nvp70mp4zlbfcinTy9C9lSGXZAmN8uGKuhWnwrFPfYupe7jQ5KQY=",
                        ],
                        "threshold": 1.0,
                        "only_pulls": False,
                        "layout": "reach, diff, flags",
                        "flags": None,
                        "paths": None,
                    }
                }
            }
        }
    }


def test_assume_flags():
    # It's deprecated, but still
    user_input = {"flags": {"some_flag": {"assume": {"branches": ["master"]}}}}
    assert do_actual_validation(
        user_input, show_secrets_for=("github", "11934774", "154468867")
    ) == {"flags": {"some_flag": {"assume": {"branches": ["^master$"]}}}}


def test_after_n_builds_flags():
    user_input = {"flags": {"some_flag": {"after_n_builds": 5}}}
    assert do_actual_validation(
        user_input, show_secrets_for=("github", "11934774", "154468867")
    ) == {"flags": {"some_flag": {"after_n_builds": 5}}}


def test_profiling_schema():
    user_input = {
        "profiling": {
            "fixes": ["batata_something::batata.txt"],
            "grouping_attributes": ["string", "str"],
            "critical_files_paths": [
                "/path/to/file.extension",
                "/path/to/dir",
                r"/path/{src|bin}/regex.{txt|php|cpp}",
                "/path/using/globs/**/file.extension",
            ],
        }
    }
    expected_result = {
        "profiling": {
            "fixes": ["^batata_something::batata.txt"],
            "grouping_attributes": ["string", "str"],
            "critical_files_paths": [
                "^/path/to/file.extension.*",
                "^/path/to/dir.*",
                "^/path/{src|bin}/regex.{txt|php|cpp}.*",
                "(?s:/path/using/globs/.*/file\\.extension.*)\\Z",
            ],
        }
    }
    result = validate_yaml(user_input)
    assert result == expected_result


def test_components_schema():
    user_input = {
        "component_management": {
            "default_rules": {
                "flag_regexes": ["global_flag"],
            },
            "individual_components": [
                {
                    "name": "fruits",
                    "component_id": "app_0",
                    "flag_regexes": ["fruit_.*", "^specific_flag$"],
                    "paths": ["src/.*"],
                    "statuses": [{"type": "patch", "name_prefix": "co", "target": 90}],
                }
            ],
        }
    }
    expected = {
        "component_management": {
            "default_rules": {
                "flag_regexes": ["global_flag"],
            },
            "individual_components": [
                {
                    "name": "fruits",
                    "component_id": "app_0",
                    "flag_regexes": ["fruit_.*", "^specific_flag$"],
                    "paths": ["src/.*"],
                    "statuses": [
                        {"type": "patch", "name_prefix": "co", "target": 90.0}
                    ],
                }
            ],
        }
    }
    result = validate_yaml(user_input)
    assert result == expected


def test_components_schema_error():
    user_input = {
        "component_management": {
            "individual_components": [
                {
                    "key": "extra",
                    "component_id": "app_0",
                    "flag_regexes": ["fruit_*", "^specific_flag$"],
                    "path_filter_regexes": ["src/.*"],
                    "statuses": [
                        {"type": "patch", "name_prefix": "co", "target": 90.0}
                    ],
                },
                {
                    "component_id": "app_0",
                    "flag_regexes": ["fruit_*", "^specific_flag$"],
                    "path_filter_regexes": ["src/.*"],
                },
            ],
        }
    }
    with pytest.raises(InvalidYamlException) as exp:
        validate_yaml(user_input)
        assert exp.error_location == [
            "component_management",
            "individual_components",
            0,
            "key",
        ]
        assert exp.error_message == "unknown field"
        assert exp.error_dict == {
            "component_management": [
                {
                    "individual_components": [
                        {
                            0: [{"key": ["unknown field"]}],
                            1: [{"component_id": ["required field"]}],
                        }
                    ]
                }
            ]
        }


def test_removed_code_behavior_config_valid():
    user_input = {
        "coverage": {
            "status": {
                "project": {
                    "some_status": {"removed_code_behavior": "removals_only"},
                }
            }
        },
        "flag_management": {
            "default_rules": {
                "statuses": [
                    {"name_prefix": "custom", "removed_code_behavior": "adjust_base"}
                ]
            },
            "individual_flags": [
                {
                    "name": "random",
                    "statuses": [
                        {
                            "name_prefix": "random-custom",
                            "removed_code_behavior": False,
                        }
                    ],
                }
            ],
        },
        "component_management": {
            "default_rules": {
                "statuses": [
                    {
                        "name_prefix": "custom",
                        "removed_code_behavior": "fully_covered_patch",
                    }
                ]
            },
            "individual_components": [
                {
                    "component_id": "random",
                    "statuses": [
                        {
                            "name_prefix": "random-custom",
                            "removed_code_behavior": "off",
                        }
                    ],
                }
            ],
        },
    }
    result = validate_yaml(user_input)
    # There's no change on the valid yaml
    assert result == user_input


def test_offset_config_error():
    user_input = {
        "flag_management": {
            "default_rules": {
                "statuses": [
                    {"name_prefix": "custom", "removed_code_behavior": "banana"}
                ]
            }
        },
    }

    with pytest.raises(InvalidYamlException) as exp:
        validate_yaml(user_input)
        assert exp.error_dict == {
            "coverage": [
                {
                    "status": [
                        {"patch": [{"some_status": [{"offset": ["unknown field"]}]}]}
                    ]
                }
            ],
            "flag_management": [
                {
                    "default_rules": [
                        {"statuses": [{0: [{"offset": ["unallowed value banana"]}]}]}
                    ]
                }
            ],
        }


def test_cli_validation():
    user_input = {
        "cli": {
            "plugins": {"pycoverage": {"report_type": "json"}},
            "runners": {
                "custom_runner": {
                    "module": "my_project.runner",
                    "class": "MyCustomRunner",
                    "params": {"randseed": 0},
                }
            },
        }
    }
    result = validate_yaml(user_input)
    # There's no change on the valid yaml
    assert result == user_input


def test_slack_app_validation():
    user_input = {"slack_app": {"enabled": True}}
    result = validate_yaml(user_input)
    assert result == user_input


def test_slack_app_validation_boolean():
    user_input = {"slack_app": True}
    result = validate_yaml(user_input)
    assert result == user_input
