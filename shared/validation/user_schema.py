flag_name = {"type": "string", "minlength": 1, "maxlength": 45, "regex": r"^[\w\.\-]+$"}

branches_structure = {
    "type": "list",
    "schema": {"type": "string", "nullable": True, "coerce": "branch_name"},
    "nullable": True,
}

layout_structure = {"type": "string", "comma_separated_strings": True, "nullable": True}

path_list_structure = {
    "type": "list",
    "nullable": True,
    "schema": {"type": "string", "coerce": "regexify_path_pattern"},
}

flag_list_structure = {
    "type": "list",
    "nullable": True,
    "schema": {"type": "string", "regex": r"^[\w\.\-]{1,45}$"},
}

status_common_config = {
    "base": {"type": "string", "allowed": ("parent", "pr", "auto")},
    "branches": branches_structure,
    "disable_approx": {"type": "boolean"},
    "enabled": {"type": "boolean"},
    "if_ci_failed": {
        "type": "string",
        "allowed": ("success", "failure", "error", "ignore"),
    },
    "if_no_uploads": {
        "type": "string",
        "allowed": ("success", "failure", "error", "ignore"),
    },
    "if_not_found": {
        "type": "string",
        "allowed": ("success", "failure", "error", "ignore"),
    },
    "informational": {"type": "boolean"},
    "measurement": {
        "type": "string",
        "nullable": True,
        "allowed": ("line", "statement", "branch", "method", "complexity"),
    },
    "only_pulls": {"type": "boolean"},
    "skip_if_assumes": {"type": "boolean"},
    "removed_code_behavior": {
        "type": ["string", "boolean"],
        "allowed": (
            "removals_only",
            "adjust_base",
            "fully_covered_patch",
            "off",
            False,
        ),
    },
}

percent_type_or_auto = {
    "type": ["string", "number"],
    "anyof": [{"allowed": ["auto"]}, {"regex": r"(\d+)(\.\d+)?%?"}],
    "nullable": True,
    "coerce": "percentage_to_number_or_auto",
}

percent_type = {
    "type": ["string", "number"],
    "regex": r"(\d+)(\.\d+)?%?",
    "nullable": True,
    "coerce": "percentage_to_number",
}

custom_status_common_config = {
    "name_prefix": {"type": "string", "regex": r"^[\w\-\.]+$"},
    "type": {"type": "string", "allowed": ("project", "patch", "changes")},
    "target": percent_type_or_auto,
    "threshold": percent_type,
}

flag_status_base_attributes = {
    **status_common_config,
    "paths": path_list_structure,
    "carryforward_behavior": {
        "type": "string",
        "allowed": ("include", "exclude", "pass"),
    },
    "flag_coverage_not_uploaded_behavior": {
        "type": "string",
        "allowed": ("include", "exclude", "pass"),
    },
}

status_standard_attributes = {
    "flags": flag_list_structure,
    **flag_status_base_attributes,
}

flag_status_attributes = {**flag_status_base_attributes, **custom_status_common_config}

component_status_attributes = {**status_common_config, **custom_status_common_config}

notification_standard_attributes = {
    "url": {"type": "string", "coerce": "secret", "nullable": True},
    "branches": branches_structure,
    "threshold": percent_type,
    "message": {"type": "string"},
    "flags": flag_list_structure,
    "base": {"type": "string", "allowed": ("parent", "pr", "auto")},
    "only_pulls": {"type": "boolean"},
    "paths": path_list_structure,
}


flags_rule_basic_properties = {
    "statuses": {
        "type": "list",
        "schema": {"type": "dict", "schema": flag_status_attributes},
    },
    "carryforward_mode": {
        "type": "string",
        "allowed": ("all", "labels"),
    },
    "carryforward": {"type": "boolean"},
    "paths": path_list_structure,
    "ignore": path_list_structure,
    "after_n_builds": {"type": "integer", "min": 0},
}

component_rule_basic_properties = {
    "statuses": {
        "type": "list",
        "schema": {"type": "dict", "schema": component_status_attributes},
    },
    "flag_regexes": {"type": "list", "schema": {"type": "string"}},
    "paths": path_list_structure,
}

schema = {
    "codecov": {
        "type": "dict",
        "schema": {
            "url": {
                "type": "string",
                "regex": r"https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)",
            },
            "token": {"type": "string"},
            "slug": {"type": "string"},
            "bot": {"type": "string", "nullable": True},
            "branch": {"type": "string", "coerce": "branch_normalize"},
            "ci": {"type": "list", "schema": {"type": "string"}},
            "assume_all_flags": {"type": "boolean"},
            "strict_yaml_branch": {"type": "string"},
            "max_report_age": {"type": ["string", "integer", "boolean"]},
            "disable_default_path_fixes": {"type": "boolean"},
            "require_ci_to_pass": {"type": "boolean"},
            "allow_coverage_offsets": {"type": "boolean"},
            "allow_pseudo_compare": {"type": "boolean"},
            "archive": {"type": "dict", "schema": {"uploads": {"type": "boolean"}}},
            "notify": {
                "type": "dict",
                "schema": {
                    "after_n_builds": {"type": "integer", "min": 0},
                    "countdown": {"type": "integer"},
                    "delay": {"type": "integer"},
                    "wait_for_ci": {"type": "boolean"},
                    "require_ci_to_pass": {"type": "boolean"},  # [DEPRECATED]
                    "manual_trigger": {"type": "boolean"},
                },
            },
            "ui": {
                "type": "dict",
                "schema": {
                    "hide_density": {
                        "anyof": [
                            {"type": "boolean"},
                            {"type": "list", "schema": {"type": "string"}},
                        ]
                    },
                    "hide_complexity": {
                        "anyof": [
                            {"type": "boolean"},
                            {"type": "list", "schema": {"type": "string"}},
                        ]
                    },
                    "hide_contexual": {"type": "boolean"},
                    "hide_sunburst": {"type": "boolean"},
                    "hide_search": {"type": "boolean"},
                },
            },
        },
    },
    "coverage": {
        "type": "dict",
        "schema": {
            "precision": {"type": "integer", "min": 0, "max": 99},
            "round": {"type": "string", "allowed": ("down", "up", "nearest")},
            "range": {"type": "list", "maxlength": 2, "coerce": "string_to_range"},
            "notify": {
                "type": "dict",
                "schema": {
                    "irc": {
                        "type": "dict",
                        "keysrules": {"type": "string", "regex": r"^[\w\-\.]+$"},
                        "valuesrules": {
                            "type": "dict",
                            "schema": {
                                "channel": {"type": "string"},
                                "server": {"type": "string"},
                                "password": {
                                    "type": "string",
                                    "coerce": "secret",
                                    "nullable": True,
                                },
                                "nickserv_password": {
                                    "type": "string",
                                    "coerce": "secret",
                                },
                                "notice": {"type": "boolean"},
                                **notification_standard_attributes,
                            },
                        },
                    },
                    "slack": {
                        "type": "dict",
                        "keysrules": {"type": "string", "regex": r"^[\w\-\.]+$"},
                        "valuesrules": {
                            "type": "dict",
                            "schema": {
                                "attachments": layout_structure,
                                **notification_standard_attributes,
                            },
                        },
                    },
                    "gitter": {
                        "type": "dict",
                        "keysrules": {"type": "string", "regex": r"^[\w\-\.]+$"},
                        "valuesrules": {
                            "type": "dict",
                            "schema": {**notification_standard_attributes},
                        },
                    },
                    "hipchat": {
                        "type": "dict",
                        "keysrules": {"type": "string", "regex": r"^[\w\-\.]+$"},
                        "valuesrules": {
                            "type": "dict",
                            "schema": {
                                "card": {"type": "boolean"},
                                "notify": {"type": "boolean"},
                                **notification_standard_attributes,
                            },
                        },
                    },
                    "webhook": {
                        "type": "dict",
                        "keysrules": {"type": "string", "regex": r"^[\w\-\.]+$"},
                        "valuesrules": {
                            "type": "dict",
                            "schema": {**notification_standard_attributes},
                        },
                    },
                    "email": {
                        "type": "dict",
                        "keysrules": {"type": "string", "regex": r"^[\w\-\.]+$"},
                        "valuesrules": {
                            "type": "dict",
                            "schema": {
                                "to": {
                                    "type": "list",
                                    "schema": {"type": "string", "coerce": "secret"},
                                },
                                "layout": layout_structure,
                                **notification_standard_attributes,
                            },
                        },
                    },
                },
            },
            "status": {
                "type": ["boolean", "dict"],
                "schema": {
                    "default_rules": {
                        "type": "dict",
                        "schema": {
                            "flag_coverage_not_uploaded_behavior": {
                                "type": "string",
                                "allowed": ("include", "exclude", "pass"),
                            },
                            "carryforward_behavior": {
                                "type": "string",
                                "allowed": ("include", "exclude", "pass"),
                            },
                        },
                    },
                    "project": {
                        "type": ["dict", "boolean"],
                        "keysrules": {"type": "string", "regex": r"^[\w\-\.]+$"},
                        "valuesrules": {
                            "nullable": True,
                            "type": ["dict", "boolean"],
                            "schema": {
                                "target": percent_type_or_auto,
                                "include_changes": percent_type_or_auto,
                                "threshold": percent_type,
                                **status_standard_attributes,
                            },
                        },
                    },
                    "patch": {
                        "type": ["dict", "boolean"],
                        "keysrules": {"type": "string", "regex": r"^[\w\-\.]+$"},
                        "valuesrules": {
                            "type": ["dict", "boolean"],
                            "nullable": True,
                            "schema": {
                                "target": percent_type_or_auto,
                                "include_changes": percent_type_or_auto,
                                "threshold": percent_type,
                                **status_standard_attributes,
                            },
                        },
                    },
                    "changes": {
                        "type": ["dict", "boolean"],
                        "keysrules": {"type": "string", "regex": r"^[\w\-\.]+$"},
                        "valuesrules": {
                            "type": ["dict", "boolean"],
                            "nullable": True,
                            "schema": status_standard_attributes,
                        },
                    },
                    "no_upload_behavior": {
                        "type": "string",
                        "allowed": ("pass", "fail"),
                    },
                },
            },
        },
    },
    "parsers": {
        "type": "dict",
        "schema": {
            "go": {"type": "dict", "schema": {"partials_as_hits": {"type": "boolean"}}},
            "javascript": {
                "type": "dict",
                "schema": {"enable_partials": {"type": "boolean"}},
            },
            "v1": {
                "type": "dict",
                "schema": {"include_full_missed_files": {"type": "boolean"}},
            },  # [DEPRECATED]
            "gcov": {
                "type": "dict",
                "schema": {
                    "branch_detection": {
                        "type": "dict",
                        "schema": {
                            "conditional": {"type": "boolean"},
                            "loop": {"type": "boolean"},
                            "method": {"type": "boolean"},
                            "macro": {"type": "boolean"},
                        },
                    }
                },
            },
            "jacoco": {
                "type": "dict",
                "schema": {"partials_as_hits": {"type": "boolean"}},
            },
        },
    },
    "ignore": path_list_structure,
    "fixes": {
        "type": "list",
        "schema": {"type": "string", "coerce": "regexify_path_fix"},
    },
    "flags": {
        "type": "dict",
        "keysrules": flag_name,
        "valuesrules": {
            "type": "dict",
            "schema": {
                "joined": {"type": "boolean"},
                "carryforward": {"type": "boolean"},
                "carryforward_mode": {
                    "type": "string",
                    "allowed": ("all", "labels"),
                },
                "required": {"type": "boolean"},
                "ignore": path_list_structure,
                "paths": path_list_structure,
                "assume": {
                    "type": ["boolean", "string", "dict"],
                    "schema": {"branches": branches_structure},
                },
                "after_n_builds": {"type": "integer", "min": 0},
            },
        },
    },
    "flag_management": {
        "type": "dict",
        "schema": {
            "default_rules": {"type": "dict", "schema": flags_rule_basic_properties},
            "individual_flags": {
                "type": "list",
                "schema": {
                    "type": "dict",
                    "schema": {
                        **flags_rule_basic_properties,
                        "name": flag_name,
                    },
                },
            },
        },
    },
    "component_management": {
        "type": "dict",
        "schema": {
            "default_rules": {
                "type": "dict",
                "schema": component_rule_basic_properties,
            },
            "individual_components": {
                "type": "list",
                "schema": {
                    "type": "dict",
                    "schema": {
                        **component_rule_basic_properties,
                        "name": {"type": "string"},
                        "component_id": {"type": "string", "required": True},
                    },
                },
            },
        },
    },
    "comment": {
        "type": ["dict", "boolean"],
        "schema": {
            "layout": {
                "type": "string",
                "comma_separated_strings": True,
                "nullable": True,
            },
            "require_changes": {"type": "boolean"},
            "require_base": {"type": "boolean"},
            "require_head": {"type": "boolean"},
            "show_critical_paths": {"type": "boolean"},
            "branches": branches_structure,
            "paths": path_list_structure,  # DEPRECATED
            "flags": flag_list_structure,  # DEPRECATED
            "behavior": {
                "type": "string",
                "allowed": ("default", "once", "new", "spammy"),
            },
            "after_n_builds": {"type": "integer", "min": 0},
            "show_carryforward_flags": {"type": "boolean"},
            "hide_comment_details": {"type": "boolean"},
        },
    },
    "github_checks": {
        "type": ["dict", "boolean"],
        "schema": {"annotations": {"type": "boolean"}},
    },
    "profiling": {
        "type": "dict",
        "schema": {
            "fixes": {
                "type": "list",
                "schema": {"type": "string", "coerce": "regexify_path_fix"},
            },
            "grouping_attributes": {"type": "list", "schema": {"type": "string"}},
            "critical_files_paths": {
                "type": "list",
                "schema": {"type": "string", "coerce": "regexify_path_pattern"},
            },
        },
    },
    "beta_groups": {"type": "list", "schema": {"type": "string"}},
}
