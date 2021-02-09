import logging

from voluptuous import Schema, Optional, MultipleInvalid, Or, And, Match, Range, Length
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


def get_new_schema(show_secrets):
    user_given_title = Match(
        r"^[\w\-\.]+$",
        msg="Must consist only of alphanumeric characters, '_', '-', or '.'",
    )
    flag_name = And(
        Length(min=1, max=45),
        Match(
            r"^[\w\.\-]+$",
            msg="Must consist only of alphanumeric characters, '_', '-', or '.'",
        ),
    )
    percent_type = PercentSchemaField().validate
    branch_structure = BranchSchemaField().validate
    branches_regexp = Match(r"")
    user_given_regex = UserGivenBranchRegex().validate
    layout_structure = LayoutStructure().validate
    path_structure = PathPatternSchemaField().validate
    base_structure = Or("parent", "pr", "auto")
    branch = BranchSchemaField().validate
    url = Match(
        r"https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)",
        msg="Must be a valid URL",
    )

    notification_standard_attributes = {
        Optional("url"): Or(None, UserGivenSecret(show_secret=show_secrets).validate),
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
            None, "line", "statement", "branch", "method", "complexity",
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
                Optional("bot"): Or(None, str),
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
                    Optional("after_n_builds"): Range(min=0),
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
                Optional("precision"): Range(min=0, max=99),
                Optional("round"): Or("down", "up", "nearest"),
                Optional("range"): CoverageRangeSchemaField().validate,
                Optional("notify"): {
                    Optional("irc"): {
                        user_given_title: {
                            Optional("channel"): str,
                            Optional("server"): str,
                            Optional("password"): UserGivenSecret(
                                show_secret=show_secrets
                            ).validate,
                            Optional("nickserv_password"): UserGivenSecret(
                                show_secret=show_secrets
                            ).validate,
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
                            "to": [
                                And(
                                    str,
                                    UserGivenSecret(show_secret=show_secrets).validate,
                                )
                            ],
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
            Optional("fixes"): Or(None, [CustomFixPathSchemaField().validate]),
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
                    Optional("after_n_builds"): Range(min=0),
                    Optional("show_carryforward_flags"): bool,
                    Optional("flags"): Or(None, [flag_name]),  # DEPRECATED
                    Optional("paths"): Or(None, [path_structure]),  # DEPRECATED
                },
            ),
            Optional("github_checks"): Or(bool, {Optional("annotations"): bool}),
        },
        required=True,
    )
