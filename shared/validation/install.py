"""Configuration options that affect an entire instance of Codecov"""

import logging

from shared.utils.enums import TaskConfigGroup
from shared.validation.user_schema import schema as user_yaml_schema
from shared.validation.validator import CodecovYamlValidator

log = logging.getLogger(__name__)


def check_task_config_key(field, value, error):
    if value == "celery":
        return
    if value in set(group.value for group in TaskConfigGroup):
        return
    error(field, "Not a valid TaskConfigGroup")


# Bot is a git provider account configured to be used in place of another
bot_details_fields = {
    # This is a PAT for some provider account that is going to be used as a bot
    "key": {"type": "string", "required": True},
    # This is used only for Bitbucket (uses Oauth1)
    "secret": {"type": "string"},
    # Identifies the bot in the logs
    "username": {"type": "string"},
}

# Credentials used by the OAuth App used when logging into Codecov UI
# note: the OAuth App acts in behalf of the user. The user will need to authorize it
# and enter user's own credentials for logging into the git provider
oauth_credential_fields = {
    "client_id": {"type": "string"},
    "client_secret": {"type": "string"},
    # The URI to redirect the user after authorization is granted to the OAuth App
    "redirect_uri": {"type": "string"},
}

# Default app [GitHub exclusive] - Credentials for a GitHub app used by this installation
# note: these credentials are used to get access_tokens for installations
GitHub_app_fields = {
    "expires": {"type": "integer"},
    "id": {"type": "integer", "required": True},
    "pem": {"type": ["string", "dict"], "required": True},
}

default_service_fields = {
    "verify_ssl": {"type": "boolean"},
    "ssl_pem": {"type": "string"},
    **oauth_credential_fields,
    "url": {"type": "string"},
    "api_url": {"type": "string"},
    # bot [enterprise (self-hosted)] - Bot that is used for all repos belonging to a given service.
    # bot [cloud] - Used as public bot fallback if bots.tokenless is not provided.
    "bot": {
        "type": "dict",
        "schema": bot_details_fields,
    },
    # global_upload_token [enterprise (self-hosted)] - Master upload token.
    # Any upload (for any repo) made to the instance using this token will be validated.
    "global_upload_token": {"type": "string"},
    "organizations": {"type": "list", "schema": {"type": "string"}},
    "webhook_secret": {"type": "string"},
    # bots - Function-specific bots used as fallbacks for public repos
    # Certain functions in the torngit adapter will use one of these tokens if none is present.
    # 'bots.tokenless' is the default fallback
    "bots": {
        "type": "dict",
        "schema": {
            "read": {
                "type": "dict",
                "schema": bot_details_fields,
            },
            "comment": {
                "type": "dict",
                "schema": bot_details_fields,
            },
            "status": {
                "type": "dict",
                "schema": bot_details_fields,
            },
            "tokenless": {
                "type": "dict",
                "schema": bot_details_fields,
            },
        },
    },
}

enterprise_queue_fields = {
    "type": "dict",
    "schema": {
        "soft_timelimit": {"type": "integer"},
        "hard_timelimit": {"type": "integer"},
    },
}

default_task_fields = {
    "queue": {"type": "string"},
    "timeout": {"type": "integer"},
    "interval_seconds": {
        "type": "integer",
        "min": 0,
    },
    "enterprise": {**enterprise_queue_fields},
}

config_schema = {
    "setup": {
        "type": "dict",
        "schema": {
            "cache": {
                "type": "dict",
                "schema": {
                    "chunks": {"type": "integer"},
                    "diff": {"type": "integer"},
                    "tree": {"type": "integer"},
                    "uploads": {"type": "integer"},
                    "yaml": {"type": "integer"},
                },
            },
            "legacy_report_style": {"type": "boolean"},
            "loglvl": {"type": "string", "allowed": ("INFO",)},
            "max_sessions": {"type": "integer"},
            "debug": {"type": "boolean"},
            "codecov_url": {"type": "string"},
            "codecov_api_url": {"type": "string"},
            "webhook_url": {"type": "string"},
            "api_cors_allowed_origins": {"type": "string"},
            "codecov_dashboard_url": {"type": "string"},
            "enterprise_license": {"type": "string"},
            "admins": {
                "type": "list",
                "schema": {
                    "type": "dict",
                    "schema": {
                        "service": {"type": "string"},
                        "username": {"type": "string"},
                    },
                },
            },
            "api_allowed_hosts": {"type": "list", "schema": {"type": "string"}},
            "secure_cookie": {"type": "boolean"},
            "pubsub": {
                "type": "dict",
                "schema": {
                    "project_id": {"type": "string"},
                    "topic": {"type": "string"},
                    "enabled": {"type": "boolean"},
                },
            },
            "marketo": {
                "type": "dict",
                "schema": {
                    "client_id": {"type": "string"},
                    "client_secret": {"type": "string"},
                    "base_url": {"type": "string"},
                    "enabled": {"type": "boolean"},
                },
            },
            "http": {
                "type": "dict",
                "schema": {
                    "timeouts": {
                        "type": "dict",
                        "schema": {
                            "external": {"type": "integer"},
                            "connect": {"type": "integer"},
                            "receive": {"type": "integer"},
                        },
                    },
                    "cookie_secret": {"type": "string"},
                    "force_https": {"type": "boolean"},
                },
            },
            "encryption_secret": {"type": "string"},
            "encryption": {
                "type": "dict",
                "schema": {
                    "keys": {
                        "type": "list",
                        "schema": {
                            "type": "dict",
                            "schema": {
                                "code": {"type": "string"},
                                "value": {"type": "string"},
                            },
                        },
                    },
                    "yaml_secret": {"type": "string"},
                    "write_key": {"type": "string"},
                },
            },
            "media": {
                "type": "dict",
                "schema": {
                    "assets": {"type": "string"},
                    "dependancies": {"type": "string"},
                },
            },
            "tasks": {
                "type": "dict",
                "keysrules": {"type": "string", "check_with": check_task_config_key},
                "valuesrules": {
                    "type": "dict",
                    "oneof": [
                        # Regular tasks config
                        {"schema": {**default_task_fields}},
                        # Special value for 'celery' key
                        {
                            "schema": {
                                "default_queue": {"type": "string"},
                                "acks_late": {"type": "boolean"},
                                "prefetch": {"type": "integer"},
                                "soft_timelimit": {"type": "integer"},
                                "hard_timelimit": {"type": "integer"},
                                "enterprise": {**enterprise_queue_fields},
                                "worker_max_memory_per_child": {"type": "integer"},
                            }
                        },
                    ],
                },
            },
            "upload_processing_delay": {"type": "integer"},
            "skip_feature_cache": {"type": "boolean"},
            "timeseries": {
                "type": "dict",
                "schema": {"enabled": {"type": "boolean"}},
            },
            "telemetry": {
                "type": "dict",
                "schema": {
                    "enabled": {"type": "boolean"},
                    "admin_email": {"type": "string"},
                    "anonymous": {"type": "boolean"},
                    "endpoint_override": {"type": "string"},
                },
            },
            "health_check": {
                "type": "dict",
                "schema": {
                    "enabled": {"type": "boolean"},
                },
            },
            "push_webhook_ignore_repo_names": {
                "type": "list",
                "schema": {"type": "string"},
            },
            # guest_access [enterprise (self-hosted)] - Wether to allow non-logged in users to access the UI in this Codecov instance
            "guest_access": {"type": "boolean"},
        },
    },
    "services": {
        "type": "dict",
        "schema": {
            "external_dependencies_folder": {"type": "string"},
            "google_analytics_key": {"type": "string"},
            "minio": {
                "type": "dict",
                "schema": {
                    "host": {"type": "string"},
                    "port": {"type": "integer"},
                    "hash_key": {"type": "string"},
                    "iam_auth": {"type": "boolean"},
                    "iam_endpoint": {"type": "string", "nullable": True},
                    "access_key_id": {"type": "string"},
                    "secret_access_key": {"type": "string"},
                    "bucket": {"type": "string"},
                    "region": {"type": "string"},
                    "expire_raw_after_n_days": {"type": "boolean"},
                    "periodic_callback_ms": {"type": ("boolean", "integer")},
                    "verify_ssl": {"type": "boolean"},
                },
            },
            "gcp": {
                "type": "dict",
                "schema": {"google_credentials_location": {"type": "string"}},
            },
            "aws": {
                "type": "dict",
                "schema": {
                    "region_name": {"type": "string"},
                    "resource": {"type": "string"},
                },
            },
            "chosen_storage": {"type": "string"},
            "database_url": {"type": "string"},
            "timeseries_database_url": {"type": "string"},
            "database": {
                "type": "dict",
                "schema": {"conn_max_age": {"type": "integer"}},
            },
            "redis_url": {"type": "string"},
            "github_marketplace": {
                "type": "dict",
                "schema": {"use_stubbed": {"type": "boolean"}},
            },
            "stripe": {"type": "dict", "schema": {"api_key": {"type": "string"}}},
            "celery_broker": {"type": "string"},
            "gravatar": {"type": "boolean"},
            "avatars.io": {"type": "boolean"},
            "sentry": {"type": "dict", "schema": {"server_dsn": {"type": "string"}}},
            "ci_providers": {"type": ["string", "list"], "schema": {"type": "string"}},
            "notifications": {
                "type": "dict",
                "schema": {
                    "slack": {
                        "type": ["boolean", "list"],
                        "schema": {"type": "string"},
                    },
                    "gitter": {
                        "type": ["boolean", "list"],
                        "schema": {"type": "string"},
                    },
                    "email": {
                        "type": ["boolean", "list"],
                        "schema": {"type": "string"},
                    },
                    "webhook": {
                        "type": ["boolean", "list"],
                        "schema": {"type": "string"},
                    },
                    "irc": {"type": ["boolean", "list"], "schema": {"type": "string"}},
                    "hipchat": {
                        "type": ["boolean", "list"],
                        "schema": {"type": "string"},
                    },
                },
            },
            "vsc_cache": {
                "type": "dict",
                "schema": {
                    "enabled": {"type": "boolean"},
                    "metrics_app": {"type": "string"},
                    "check_duration": {"type": "integer"},
                    "compare_duration": {"type": "integer"},
                    "status_duration": {"type": "integer"},
                },
            },
            "smtp": {
                "type": "dict",
                "schema": {
                    "host": {"type": "string"},
                    "port": {"type": "integer"},
                    "username": {"type": "string", "required": False},
                    "password": {"type": "string", "required": False},
                },
                "required": False,
            },
        },
    },
    "site": {"type": "dict", "schema": user_yaml_schema},
    "additional_user_yamls": {
        "type": "list",
        "schema": {
            "type": "dict",
            "schema": {
                "percentage": {"type": "integer"},
                "name": {"type": "string"},
                "override": {"type": "dict", "schema": user_yaml_schema},
            },
        },
    },
    "github": {
        "type": "dict",
        "schema": {
            **default_service_fields,
            # integration - Credentials for the default Codecov App
            "integration": {
                "type": "dict",
                "schema": GitHub_app_fields,
            },
            # dedicated_apps - Dedicated apps are used in specific tasks.
            # They can have a different set of permissions than the default Codecov App, allowing us to provide different opt-in services
            "dedicated_apps": {
                "type": "dict",
                "valuesrules": {"type": "dict", "schema": GitHub_app_fields},
            },
        },
    },
    "bitbucket": {"type": "dict", "schema": {**default_service_fields}},
    "bitbucket_server": {"type": "dict", "schema": {**default_service_fields}},
    "github_enterprise": {"type": "dict", "schema": {**default_service_fields}},
    "gitlab": {"type": "dict", "schema": {**default_service_fields}},
    "gitlab_enterprise": {"type": "dict", "schema": {**default_service_fields}},
    "compatibility": {
        "type": "dict",
        "schema": {"flag_pattern_matching": {"type": "boolean"}},
    },
    "migrations": {"type": "dict", "schema": {"skip_risky_steps": {"type": "boolean"}}},
}


def pre_process_config(inputted_dict):
    # TODO: Add user yaml preprocess to here
    pass


def validate_install_configuration(inputted_dict):
    pre_process_config(inputted_dict)
    validator = CodecovYamlValidator(show_secret=True)
    is_valid = validator.validate(inputted_dict, config_schema)
    if not is_valid:
        log.warning(
            "Configuration considered invalid, using dict as it is",
            extra=dict(errors=validator.errors),
        )
    return validator.document
