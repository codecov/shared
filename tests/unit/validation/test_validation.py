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
                        "(?s:vendor/.*/[^\\/]+)\\Z",
                        "(?s:.*/[^\\/]+\\.pb\\.go.*)\\Z",
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
                "individual_flags": [{"name": "cawcaw", "paths": ["banana"]}],
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
                "individual_flags": [{"name": "cawcaw", "paths": ["^banana.*"]}],
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
                }
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
                }
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
            "ignore": ["Pods/.*",],
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
            "ignore": ["Pods/.*",],
        }
        with pytest.raises(InvalidYamlException) as exc:
            validate_yaml(user_input)
        assert exc.value.error_location == ["coverage", "range"]
        assert exc.value.error_message == "must be of list type"

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
                "status": {"project": {"default": {"base": "auto",}}},
            },
            "ignore": ["Pods/.*",],
        }
        expected_result = {
            "coverage": {
                "round": "down",
                "precision": 2,
                "range": [70.0, 100.0],
                "status": {"project": {"default": {"base": "auto",}}},
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
                "range": [70.0, 100.0],
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
    user_input = {
        "codecov": {"branch": "origin/pterosaur"},
    }
    res = do_actual_validation(user_input, show_secrets_for=None)
    assert res == {
        "codecov": {"branch": "pterosaur"},
    }


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
