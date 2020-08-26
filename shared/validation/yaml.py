import logging
import re

from schema import Schema, Optional, Or, And, SchemaError, Regex
from shared.validation.exceptions import InvalidYamlException
from shared.validation.helpers import (
    PercentSchemaField,
    BranchSchemaField,
    UserGivenBranchRegex,
    LayoutStructure,
    PathPatternSchemaField,
    UserGivenSecret,
    CoverageRangeSchemaField,
    CustomFixPathSchemaField,
)
from .schema import get_new_schema

log = logging.getLogger(__name__)

# *** Reminder: when changes are made to YAML validation, you will need to update the version of shared in both
# worker (to apply the changes) AND codecov-api (so the validate route reflects the changes) ***


def validate_yaml(inputted_yaml_dict, show_secrets=False):
    """Receives a user-given yaml dict, validates and normalizes the fields for
        usage by other code

    Args:
        inputted_yaml_dict (dict): The yaml as parsed by a yaml parser and turned into a dict

    Returns:
        dict: A deep copy of the dict with the fields normalized

    Raises:
        InvalidYamlException: If the yaml inputted by the user is not valid

    Note: currently testing out a different schema validation library (voluptuous) that provides more control over error messaging and better-formatted
    error message, in the interest of returning more user-friendly yaml validation errors. Since yaml validation is an important part of upload processing
    and we don't want to accidentally break it, we're testing with both the original and new schemas for now and will log any discrepancies between them.
    """
    pre_process_yaml(inputted_yaml_dict)
    original_yaml_schema = get_schema(show_secrets)
    new_yaml_schema = get_new_schema(show_secrets)

    # Set up variables to compare new and original schema - see "note" in function documentation for more context
    (
        original_schema_valid,
        original_schema_result,
        original_schema_exception,
        original_schema_error_message,
    ) = (None, None, None, None)
    (
        new_schema_valid,
        new_schema_result,
        new_schema_exception,
        new_schema_error_message,
    ) = (None, None, None, None)

    # Original schema
    try:
        original_schema_result = original_yaml_schema.validate(inputted_yaml_dict)
        original_schema_valid = True
    except SchemaError as e:
        original_schema_valid = False
        original_schema_exception = e

        good_messages = []
        for message in e.autos:
            if message:
                match = re.match(r"Key '(\w+)?' error:", message)
                if match:
                    good_messages.append(match.group(1))
        log.warning(
            "Unable to validate yaml",
            extra=dict(user_input=inputted_yaml_dict),
            exc_info=True,
        )
        readable_messages = "->".join(good_messages)
        original_schema_error_message = f"Path: {readable_messages}"

    # New schema
    try:
        new_schema_result = new_yaml_schema(inputted_yaml_dict)
        new_schema_valid = True
    except Exception as e:
        new_schema_valid = False
        new_schema_exception = e

        new_schema_error_message = e.errors if hasattr(e, "errors") else str(e)

    # log discrepancy in validation
    if original_schema_valid != new_schema_valid:
        log.warning(
            "YAML validation returned different validation result for new and original schema",
            extra=dict(
                user_input=inputted_yaml_dict,
                new_schema_valid=new_schema_valid,
                original_schema_valid=original_schema_valid,
                new_schema_error_message=new_schema_error_message,
                original_schema_error_message=original_schema_error_message,
            ),
        )

    # log discrepancy in validated result
    elif original_schema_result != new_schema_result:
        log.warning(
            "Validated YAML differs between new and original schema",
            extra=dict(
                user_input=inputted_yaml_dict,
                new_schema_result=new_schema_result,
                original_schema_result=original_schema_result,
                new_schema_error_message=new_schema_error_message,
                original_schema_error_message=original_schema_error_message,
            ),
        )

    if original_schema_valid is False:
        raise InvalidYamlException(
            original_schema_error_message, original_schema_exception
        )

    return post_process(original_schema_result)


def get_schema(show_secrets):
    user_given_title = Regex(r"^[\w\-\.]+$")
    flag_name = Regex(r"^[\w\.\-]{1,45}$")
    percent_type = PercentSchemaField()
    branch_structure = BranchSchemaField()
    branches_regexp = Regex(r"")
    user_given_regex = UserGivenBranchRegex()
    layout_structure = LayoutStructure()
    path_structure = PathPatternSchemaField()
    base_structure = Or("parent", "pr", "auto")
    branch = BranchSchemaField()
    url = Regex(
        r"https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)"
    )

    notification_standard_attributes = {
        Optional("url"): Or(None, UserGivenSecret(show_secret=show_secrets)),
        Optional("branches"): Or(None, [branches_regexp]),
        Optional("threshold"): Or(None, percent_type),
        Optional("message"): str,  # TODO (Thiago): Convert this to deal with handlebars
        Optional("flags"): Or(None, [flag_name]),
        Optional("base"): base_structure,
        Optional("only_pulls"): bool,
        Optional("paths"): Or(None, [path_structure]),
    }

    status_standard_attributes = {
        Optional("base"): base_structure,
        Optional("branches"): Or(None, [user_given_regex]),
        Optional("disable_approx"): bool,
        Optional("enabled"): bool,
        Optional("flags"): Or(None, [flag_name]),
        Optional("if_ci_failed"): Or("success", "failure", "error", "ignore"),
        Optional("if_no_uploads"): Or("success", "failure", "error", "ignore"),
        Optional("if_not_found"): Or("success", "failure", "error", "ignore"),
        Optional("informational"): bool,
        Optional("measurement"): Or(
            None, "line", "statement", "branch", "method", "complexity"
        ),
        Optional("only_pulls"): bool,
        Optional("paths"): Or(None, [path_structure]),
        Optional("skip_if_assumes"): bool,
        Optional("carryforward_behavior"): Or("include", "exclude", "pass"),
        Optional("flag_coverage_not_uploaded_behavior"): Or(
            "include", "exclude", "pass"
        ),
    }

    return Schema(
        {
            Optional("codecov"): {
                Optional("url"): url,
                Optional("token"): str,
                Optional("slug"): str,
                Optional("bot"): str,
                Optional("branch"): branch,
                Optional("ci"): [str],
                Optional("assume_all_flags"): bool,
                Optional("strict_yaml_branch"): str,
                Optional("max_report_age"): Or(str, int, bool),
                Optional("disable_default_path_fixes"): bool,
                Optional("require_ci_to_pass"): bool,
                Optional("allow_coverage_offsets"): bool,
                Optional("allow_pseudo_compare"): bool,
                Optional("archive"): {Optional("uploads"): bool},
                Optional("notify"): {
                    Optional("after_n_builds"): And(int, lambda x: x >= 0),
                    Optional("countdown"): int,
                    Optional("delay"): int,
                    Optional("wait_for_ci"): bool,
                    Optional("require_ci_to_pass"): bool,  # [DEPRECATED]
                },
                Optional("ui"): {
                    Optional("hide_density"): Or(bool, [str]),
                    Optional("hide_complexity"): Or(bool, [str]),
                    Optional("hide_contexual"): bool,
                    Optional("hide_sunburst"): bool,
                    Optional("hide_search"): bool,
                },
            },
            Optional("coverage"): {
                Optional("precision"): And(int, lambda n: 0 <= n <= 99),
                Optional("round"): And(str, Or("down", "up", "nearest")),
                Optional("range"): CoverageRangeSchemaField(),
                Optional("notify"): {
                    Optional("irc"): {
                        user_given_title: {
                            Optional("channel"): str,
                            Optional("server"): str,
                            Optional("password"): UserGivenSecret(
                                show_secret=show_secrets
                            ),
                            Optional("nickserv_password"): UserGivenSecret(
                                show_secret=show_secrets
                            ),
                            Optional("notice"): bool,
                            **notification_standard_attributes,
                        }
                    },
                    Optional("slack"): {
                        user_given_title: {
                            Optional("attachments"): layout_structure,
                            **notification_standard_attributes,
                        }
                    },
                    Optional("gitter"): {
                        user_given_title: {**notification_standard_attributes}
                    },
                    Optional("hipchat"): {
                        user_given_title: {
                            Optional("card"): bool,
                            Optional("notify"): bool,
                            **notification_standard_attributes,
                        }
                    },
                    Optional("webhook"): {
                        user_given_title: {**notification_standard_attributes}
                    },
                    Optional("email"): {
                        user_given_title: {
                            Optional("layout"): layout_structure,
                            "to": [And(str, UserGivenSecret(show_secret=show_secrets))],
                            **notification_standard_attributes,
                        }
                    },
                },
                Optional("status"): Or(
                    bool,
                    {
                        Optional("default_rules"): {
                            Optional("carryforward_behavior"): Or(
                                "include", "exclude", "pass"
                            ),
                            Optional("flag_coverage_not_uploaded_behavior"): Or(
                                "include", "exclude", "pass"
                            ),
                        },
                        Optional("project"): Or(
                            bool,
                            {
                                user_given_title: Or(
                                    None,
                                    bool,
                                    {
                                        Optional("target"): Or("auto", percent_type),
                                        Optional("include_changes"): Or(
                                            "auto", percent_type
                                        ),
                                        Optional("threshold"): percent_type,
                                        **status_standard_attributes,
                                    },
                                )
                            },
                        ),
                        Optional("patch"): Or(
                            bool,
                            {
                                user_given_title: Or(
                                    None,
                                    bool,
                                    {
                                        Optional("target"): Or("auto", percent_type),
                                        Optional("include_changes"): Or(
                                            "auto", percent_type
                                        ),
                                        Optional("threshold"): percent_type,
                                        **status_standard_attributes,
                                    },
                                )
                            },
                        ),
                        Optional("changes"): Or(
                            bool,
                            {
                                user_given_title: Or(
                                    None, bool, status_standard_attributes
                                )
                            },
                        ),
                    },
                ),
            },
            Optional("parsers"): {
                Optional("javascript"): {"enable_partials": bool},
                Optional("v1"): {"include_full_missed_files": bool},  # [DEPRECATED]
                Optional("gcov"): {
                    "branch_detection": {
                        "conditional": bool,
                        "loop": bool,
                        "method": bool,
                        "macro": bool,
                    }
                },
            },
            Optional("ignore"): Or(None, [path_structure]),
            Optional("fixes"): Or(None, [CustomFixPathSchemaField()]),
            Optional("flags"): {
                user_given_title: {
                    Optional("joined"): bool,
                    Optional("carryforward"): bool,
                    Optional("required"): bool,
                    Optional("ignore"): Or(None, [path_structure]),
                    Optional("paths"): Or(None, [path_structure]),
                    Optional("assume"): Or(
                        bool, {"branches": Or(None, [user_given_regex])}
                    ),
                }
            },
            Optional("comment"): Or(
                bool,
                {
                    Optional("layout"): Or(None, layout_structure),
                    Optional("require_changes"): bool,
                    Optional("require_base"): bool,
                    Optional("require_head"): bool,
                    Optional("branches"): Or(None, [user_given_regex]),
                    Optional("behavior"): Or("default", "once", "new", "spammy"),
                    Optional("after_n_builds"): And(int, lambda x: x >= 0),
                    Optional("show_carryforward_flags"): bool,
                    Optional("flags"): Or(None, [flag_name]),  # DEPRECATED
                    Optional("paths"): Or(None, [path_structure]),  # DEPRECATED
                },
            ),
            Optional("github_checks"): Or(bool, {Optional("annotations"): bool}),
        }
    )


def post_process(validated_yaml_dict):
    """Does any needed post-processings

    Args:
        validated_yaml_dict (dict): The dict after validated

    Returns:
        (dict): The post-processed dict to be used

    """
    return validated_yaml_dict


def pre_process_yaml(inputted_yaml_dict):
    """
        Changes the inputted_yaml_dict in-place with compatibility changes that need to be done

    Args:
        inputted_yaml_dict (dict): The yaml dict inputted by the user
    """
    coverage = inputted_yaml_dict.get("coverage", {})
    if "flags" in coverage:
        inputted_yaml_dict["flags"] = coverage.pop("flags")
    if "parsers" in coverage:
        inputted_yaml_dict["parsers"] = coverage.pop("parsers")
    if "ignore" in coverage:
        inputted_yaml_dict["ignore"] = coverage.pop("ignore")
    if "fixes" in coverage:
        inputted_yaml_dict["fixes"] = coverage.pop("fixes")
    if inputted_yaml_dict.get("codecov") and inputted_yaml_dict["codecov"].get(
        "notify"
    ):
        if "require_ci_to_pass" in inputted_yaml_dict["codecov"]["notify"]:
            val = inputted_yaml_dict["codecov"]["notify"].pop("require_ci_to_pass")
            inputted_yaml_dict["codecov"]["require_ci_to_pass"] = val
