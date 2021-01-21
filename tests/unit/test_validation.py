import re
import os
from base64 import b64encode

import pytest
from schema import SchemaError
from mock import patch

from tests.base import BaseTestCase
from shared.config import get_config, ConfigHelper
from shared.validation.yaml import (
    LayoutStructure,
    validate_yaml,
    PathPatternSchemaField,
    CoverageRangeSchemaField,
    PercentSchemaField,
    CustomFixPathSchemaField,
    pre_process_yaml,
    UserGivenSecret,
)
from shared.validation.exceptions import InvalidYamlException
from shared.validation.helpers import (
    determine_path_pattern_type,
    translate_glob_to_regex,
)


class TestPathPatternSchemaField(BaseTestCase):
    def test_simple_path_structure_no_star(self):
        ps = PathPatternSchemaField()
        res = ps.validate("a/b")
        compiled = re.compile(res)
        assert compiled.match("a/b") is not None
        assert compiled.match("a/b/file_1.py") is not None
        assert compiled.match("c/a/b") is None
        assert compiled.match("a/path/b") is None
        assert compiled.match("a/path/path2/b") is None

    def test_simple_path_structure_regex(self):
        ps = PathPatternSchemaField()
        res = ps.validate("[a-z]+/test_.*")
        compiled = re.compile(res)
        assert compiled.match("perro/test_folder.py") is not None
        assert compiled.match("cachorro/test_folder.py") is not None
        assert compiled.match("cachorro/tes_folder.py") is None
        assert compiled.match("cachorro/what/test_folder.py") is None
        assert compiled.match("[/a/b") is None

    def test_simple_path_structure_one_star_end(self):
        ps = PathPatternSchemaField()
        res = ps.validate("tests/*")
        compiled = re.compile(res)
        assert compiled.match("tests/file_1.py") is not None
        assert compiled.match("tests/testeststsetetesetsfile_2.py") is not None
        assert compiled.match("tests/deep/file_1.py") is None

    def test_simple_path_structure_one_star(self):
        ps = PathPatternSchemaField()
        res = ps.validate("a/*/b")
        compiled = re.compile(res)
        assert compiled.match("a/path/b") is not None
        assert compiled.match("a/path/b/file_2.py") is not None
        assert compiled.match("a/path/b/more_path/some_file.py") is not None
        assert compiled.match("a/b") is None
        assert compiled.match("a/path/path2/b") is None

    def test_simple_path_structure_negative(self):
        ps = PathPatternSchemaField()
        res = ps.validate("!path/to/folder")
        assert res.startswith("!")
        compiled = re.compile(res[1:])
        # Check the negatives, we want `path/to/folder` files to match so we refuse them later
        assert compiled.match("path/to/folder") is not None
        assert compiled.match("path/to/folder/file_2.py") is not None
        assert compiled.match("path/to/folder/more_path/some_file.py") is not None
        assert compiled.match("a/b") is None
        assert compiled.match("path/folder") is None

    def test_simple_path_structure_double_star(self):
        ps = PathPatternSchemaField()
        res = ps.validate("a/**/b")
        compiled = re.compile(res)
        assert compiled.match("a/path/b") is not None
        assert compiled.match("a/path/b/some_file.py") is not None
        assert compiled.match("a/path/b/more_path/some_file.py") is not None
        assert compiled.match("a/path/path2/b") is not None
        assert compiled.match("a/path/path2/b/some_file.py") is not None
        assert compiled.match("a/path/path2/b/more_path/some_file.py") is not None
        assert compiled.match("a/c") is None

    def test_path_with_leading_period_slash(self):
        ps = PathPatternSchemaField()
        res = ps.validate("./src/register-test-globals.ts")
        compiled = re.compile(res)
        assert compiled.match("src/register-test-globals.ts") is not None
        second_res = ps.validate("./test/*.cc")
        second_compiled = re.compile(second_res)
        assert second_compiled.match("test/test_SW_Markov.cc") is not None

    def test_star_dot_star_pattern(self):
        ps = PathPatternSchemaField()
        res = ps.validate("test/**/*.*")
        compiled = re.compile(res)
        assert compiled.match("test/unit/presenters/goal_sparkline_test.rb") is not None

    def test_double_star_end(self):
        user_input = "Snapshots/**"
        ps = PathPatternSchemaField()
        res = ps.validate(user_input)
        compiled = re.compile(res)
        assert compiled.match("Snapshots/Snapshots/ViewController.swift") is not None


class TestLayoutStructure(BaseTestCase):
    def test_simple_layout(self):
        schema = LayoutStructure()
        result = "reach, diff, flags, files, footer"
        expected_result = "reach, diff, flags, files, footer"
        assert expected_result == schema.validate(result)

    def test_simple_layout_with_number(self):
        schema = LayoutStructure()
        result = "reach, diff, flags, files:10, footer"
        expected_result = "reach, diff, flags, files:10, footer"
        assert expected_result == schema.validate(result)

    def test_simple_layout_with_improper_number(self):
        schema = LayoutStructure()
        result = "reach, diff, flags, files:twenty, footer"
        with pytest.raises(SchemaError) as exc:
            schema.validate(result)
        assert exc.value.code == "Improper pattern for value on layout: files:twenty"

    def test_simple_layout_bad_name(self):
        schema = LayoutStructure()
        result = "reach, diff, flags, love, files, footer"
        with pytest.raises(SchemaError) as exc:
            schema.validate(result)
        assert exc.value.code == "Unexpected values on layout: love"


class TestCoverageRangeSchemaField(BaseTestCase):
    def test_simple_coverage_range(self):
        crsf = CoverageRangeSchemaField()
        assert crsf.validate([80, 90]) == [80.0, 90.0]
        assert crsf.validate("80..90") == [80.0, 90.0]
        assert crsf.validate("80...90") == [80.0, 90.0]
        assert crsf.validate("80...100") == [80.0, 100.0]
        invalid_cases = [
            "80....90",
            "80.90",
            "90..80",
            "90..80..50",
            "infinity...90",
            "80...?90",
            "80...101",
            "-80...90",
            "80...9f0",
            ["arroba", 90],
            [10, 20, 30],
            [10, 20, 30],
            ["infinity", 90],
        ]
        for invalid in invalid_cases:
            with pytest.raises(SchemaError):
                crsf.validate(invalid)


class TestPercentSchemaField(BaseTestCase):
    def test_simple_coverage_range(self):
        crsf = PercentSchemaField()
        assert crsf.validate(80) == 80.0
        assert crsf.validate(80.0) == 80.0
        assert crsf.validate("80%") == 80.0
        assert crsf.validate("80") == 80.0
        assert crsf.validate("0") == 0.0
        assert crsf.validate("150%") == 150.0
        with pytest.raises(SchemaError):
            crsf.validate("nana")
        with pytest.raises(SchemaError):
            crsf.validate("%80")
        with pytest.raises(SchemaError):
            crsf.validate("8%0%")
        with pytest.raises(SchemaError):
            crsf.validate("infinity")
        with pytest.raises(SchemaError):
            crsf.validate("nan")


class TestPatternTypeDetermination(BaseTestCase):
    def test_determine_path_pattern_type(self):
        assert determine_path_pattern_type("path/to/folder") == "path_prefix"
        assert determine_path_pattern_type("path/*/folder") == "glob"
        assert determine_path_pattern_type("path/**/folder") == "glob"
        assert determine_path_pattern_type("path/.*/folder") == "regex"
        assert determine_path_pattern_type("path/[a-z]*/folder") == "regex"
        assert determine_path_pattern_type("*/[a-z]*/folder") == "glob"
        assert determine_path_pattern_type("before/test-*::after/") == "glob"


class TestPreprocess(BaseTestCase):
    def test_preprocess_empty(self):
        user_input = {}
        expected_result = {}
        pre_process_yaml(user_input)
        assert expected_result == user_input

    def test_preprocess_none_in_fields(self):
        user_input = {"codecov": None}
        expected_result = {"codecov": None}
        pre_process_yaml(user_input)
        assert expected_result == user_input


class TestUserYamlValidation(BaseTestCase):
    def test_empty_case(self):
        user_input = {}
        expected_result = {}
        assert validate_yaml(user_input) == expected_result

    def test_simple_case(self):
        value = "github/11934774/154468867/https://hooks.slack.com/services/first_key/BE7FWCVHV/dkbfscprianc7wrb"
        encoded_value = UserGivenSecret.encode(value)
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
        assert exception.error_location == "Path: codecov->notify->after_n_builds"

    def test_positive_notify_after_n_builds(self):
        user_input = {"codecov": {"notify": {"after_n_builds": 1}}}
        res = validate_yaml(user_input)
        assert res == {"codecov": {"notify": {"after_n_builds": 1}}}

    def test_negative_comments_after_n_builds(self):
        user_input = {"comment": {"after_n_builds": -1}}
        with pytest.raises(InvalidYamlException) as exc:
            validate_yaml(user_input)
        exception = exc.value
        assert exception.error_location == "Path: comment->after_n_builds"

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
        assert exc.value.error_location == "Path: coverage->status->project->base"

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
        assert (
            exc.value.error_location == "Path: flag_management->default_rules->statuses"
        )

    def test_show_secret_case(self):
        value = "github/11934774/154468867/https://hooks.slack.com/services/first_key/BE7FWCVHV/dkbfscprianc7wrb"
        encoded_value = UserGivenSecret.encode(value)
        user_input = {
            "coverage": {
                "round": "down",
                "precision": 2,
                "range": [70.0, 100.0],
                "status": {"project": {"default": {"base": "auto",}}},
                "notify": {"irc": {"user_given_title": {"password": encoded_value}}},
            },
            "ignore": ["Pods/.*",],
        }
        expected_result = {
            "coverage": {
                "round": "down",
                "precision": 2,
                "range": [70.0, 100.0],
                "status": {"project": {"default": {"base": "auto",}}},
                "notify": {
                    "irc": {
                        "user_given_title": {
                            "password": "https://hooks.slack.com/services/first_key/BE7FWCVHV/dkbfscprianc7wrb"
                        }
                    }
                },
            },
            "ignore": ["Pods/.*",],
        }
        result = validate_yaml(user_input, show_secrets=True)
        assert result == expected_result

    def test_github_checks(self):
        user_input = {"github_checks": True}
        expected_result = {"github_checks": True}
        assert validate_yaml(user_input) == expected_result
        user_input = {"github_checks": {"annotations": False}}
        expected_result = {"github_checks": {"annotations": False}}
        assert validate_yaml(user_input) == expected_result

    def test_required_fields(self):
        # Valid beause it has all required sub-fields
        user_input = {
            "parsers": {
                "gcov": {
                    "branch_detection": {
                        "conditional": True,
                        "loop": True,
                        "method": False,
                        "macro": False,
                    }
                }
            }
        }
        expected_result = {
            "parsers": {
                "gcov": {
                    "branch_detection": {
                        "conditional": True,
                        "loop": True,
                        "method": False,
                        "macro": False,
                    }
                }
            }
        }
        assert validate_yaml(user_input) == expected_result

        # Invalid because it only specifies one sub-field but all are required
        with pytest.raises(InvalidYamlException) as exc:
            user_input = {
                "parsers": {"gcov": {"branch_detection": {"conditional": True}}}
            }
            validate_yaml(user_input)
        assert exc.value.error_location == "Path: parsers->gcov->branch_detection"

    def test_new_schema_exception_handling(self, mocker):
        # raise an exception during new schema validation
        mocker.patch(
            "shared.validation.yaml.get_new_schema",
            return_value=mocker.MagicMock(side_effect=TypeError()),
        )

        # call should complete successfully and not raise any errors when handlin the exception
        assert validate_yaml({}) == {}


class TestGlobToRegexTranslation(BaseTestCase):
    def test_translate_glob_to_regex(self):
        assert re.compile(translate_glob_to_regex("a")).match("a") is not None
        assert re.compile(translate_glob_to_regex("[abc]*")).match("a") is None
        assert re.compile(translate_glob_to_regex("[abc]*")).match("ab") is not None
        assert re.compile(translate_glob_to_regex("[abc]")).match("d") is None
        assert re.compile(translate_glob_to_regex("[a-c]")).match("b") is not None


class TestCustomFixPathSchemaField(BaseTestCase):
    def test_custom_fixpath(self):
        cfpsf = CustomFixPathSchemaField()
        res = cfpsf.validate("a::b")
        assert res == "^a::b"

    def test_custom_fixpath_removal(self):
        cfpsf = CustomFixPathSchemaField()
        res = cfpsf.validate("a/::")
        assert res == "a/::"

    def test_custom_fixpath_removal_no_slashes(self):
        cfpsf = CustomFixPathSchemaField()
        res = cfpsf.validate("a::")
        assert res == "a::"

    def test_custom_fixpath_addition(self):
        cfpsf = CustomFixPathSchemaField()
        res = cfpsf.validate("::b")
        assert res == "::b"

    def test_custom_fixpath_regex(self):
        cfpsf = CustomFixPathSchemaField()
        res = cfpsf.validate("path-*::b")
        assert res == r"(?s:path\-[^\/]+)::b"

    def test_custom_fixpath_docs_example(self):
        cfpsf = CustomFixPathSchemaField()
        res = cfpsf.validate("before/tests-*::after/")
        assert res == r"(?s:before/tests\-[^\/]+)::after/"

    def test_custom_fixpath_invalid_input(self):
        cfpsf = CustomFixPathSchemaField()
        # No "::" separator
        with pytest.raises(SchemaError):
            cfpsf.validate("beforeafter")


class TestUserGivenSecret(BaseTestCase):
    def test_simple_user_given_secret(self):
        value = "github/11934774/154468867/https://hooks.slack.com/services/first_key/BE7FWCVHV/dkbfscprianc7wrb"
        encoded_value = UserGivenSecret.encode(value)
        ugs = UserGivenSecret(show_secret=True)
        assert ugs.validate(value) == value
        assert (
            ugs.validate(encoded_value)
            == "https://hooks.slack.com/services/first_key/BE7FWCVHV/dkbfscprianc7wrb"
        )

    def test_pseudosecret_user_given_secret(self):
        value = "secret:arriba"
        ugs = UserGivenSecret(show_secret=True)
        assert ugs.validate(value) == value

    def test_b64encoded_pseudosecret_user_given_secret(self):
        encoded_value = b64encode("arriba".encode())
        value = b"secret:" + encoded_value
        value = value.decode()
        ugs = UserGivenSecret(show_secret=True)
        assert ugs.validate(value) == value

    def test_simple_user_dont_show_secret(self):
        value = "github/11934774/154468867/https://hooks.slack.com/services/first_key/BE7FWCVHV/dkbfscprianc7wrb"
        encoded_value = UserGivenSecret.encode(value)
        ugs = UserGivenSecret(show_secret=False)
        assert ugs.validate(value) == value
        assert ugs.validate(encoded_value) == encoded_value


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
        res = validate_yaml(get_config("site", default={}), show_secrets=True)
        assert res == expected_result
