import logging

from shared.validation.experimental import (
    schema as user_yaml_schema,
    CodecovYamlValidator,
)

log = logging.getLogger(__name__)

default_service_fields = {
    "verify_ssl": {"type": "boolean"},
    "ssl_pem": {"type": "string"},
    "client_id": {"type": "string"},
    "client_secret": {"type": "string"},
    "integration": {
        "type": "dict",
        "schema": {
            "expires": {"type": "integer"},
            "id": {"type": "integer"},
            "pem": {"type": ["string", "dict"]},
        },
    },
    "url": {"type": "string"},
    "api_url": {"type": "string"},
    "bot": {
        "type": "dict",
        "schema": {
            "key": {"type": "string"},
            "secret": {"type": "string"},
            "username": {"type": "string"},
        },
    },
    "organizations": {"type": "list", "schema": {"type": "string"}},
    "webhook_secret": {"type": "string"},
    "bots": {
        "type": "dict",
        "schema": {
            "read": {
                "type": "dict",
                "schema": {
                    "key": {"type": "string"},
                    "secret": {"type": "string"},
                    "username": {"type": "string"},
                },
            },
            "comment": {
                "type": "dict",
                "schema": {
                    "key": {"type": "string"},
                    "secret": {"type": "string"},
                    "username": {"type": "string"},
                },
            },
            "status": {
                "type": "dict",
                "schema": {
                    "key": {"type": "string"},
                    "secret": {"type": "string"},
                    "username": {"type": "string"},
                },
            },
        },
    },
}

default_task_fields = {"queue": {"type": "string"}}

config_schema = {
    "setup": {
        "type": "dict",
        "schema": {
            "cache": {"type": "dict", "schema": {"uploads": {"type": "integer"}}},
            "loglvl": {"type": "string", "allowed": ("INFO",)},
            "max_sessions": {"type": "integer"},
            "debug": {"type": "boolean"},
            "codecov_url": {"type": "string"},
            "codecov_api_url": {"type": "string"},
            "webhook_url": {"type": "string"},
            "api_cors_allowed_origins": {"type": "string"},
            "codecov_dashboard_url": {"type": "string"},
            "enterprise_license": {"type": "string"},
            "api_allowed_hosts": {"type": "list", "schema": {"type": "string"}},
            "segment": {
                "type": "dict",
                "schema": {"key": {"type": "string"}, "enabled": {"type": "boolean"},},
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
                "schema": {
                    "celery": {
                        "type": "dict",
                        "schema": {
                            "default_queue": {"type": "string"},
                            "acks_late": {"type": "boolean"},
                            "prefetch": {"type": "integer"},
                            "soft_timelimit": {"type": "integer"},
                            "hard_timelimit": {"type": "integer"},
                        },
                    },
                    "notify": {
                        "type": "dict",
                        "schema": {
                            "timeout": {"type": "integer"},
                            **default_task_fields,
                        },
                    },
                    "sync_teams": {"type": "dict", "schema": {**default_task_fields}},
                    "sync_repos": {"type": "dict", "schema": {**default_task_fields}},
                    "delete_owner": {"type": "dict", "schema": {**default_task_fields}},
                    "pulls": {"type": "dict", "schema": {**default_task_fields}},
                    "status": {"type": "dict", "schema": {**default_task_fields}},
                    "upload": {"type": "dict", "schema": {**default_task_fields}},
                    "archive": {"type": "dict", "schema": {**default_task_fields}},
                    "verify_bot": {"type": "dict", "schema": {**default_task_fields}},
                    "comment": {"type": "dict", "schema": {**default_task_fields}},
                    "flush_repo": {"type": "dict", "schema": {**default_task_fields}},
                    "sync_plans": {"type": "dict", "schema": {**default_task_fields}},
                    "remove_webhook": {
                        "type": "dict",
                        "schema": {**default_task_fields},
                    },
                    "synchronize": {"type": "dict", "schema": {**default_task_fields}},
                    "new_user_activated": {
                        "type": "dict",
                        "schema": {**default_task_fields},
                    },
                },
            },
            "upload_processing_delay": {"type": "integer"},
        },
    },
    "services": {
        "type": "dict",
        "schema": {
            "google_analytics_key": {"type": "string"},
            "minio": {
                "type": "dict",
                "schema": {
                    "host": {"type": "string"},
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
        },
    },
    "site": {"type": "dict", "schema": user_yaml_schema},
    "github": {"type": "dict", "schema": {**default_service_fields}},
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
            extra=dict(errors=validator.errors, inputted_dict=inputted_dict),
        )
    return validator.document
