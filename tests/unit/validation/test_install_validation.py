from shared.validation.install import log as install_log
from shared.validation.install import validate_install_configuration
from shared.yaml.validation import UserGivenSecret


def test_validate_install_configuration_empty(mocker):
    mock_warning = mocker.patch.object(install_log, "warning")
    assert validate_install_configuration({}) == {}
    assert mock_warning.call_count == 0


def test_validate_install_configuration_simple(mocker):
    mock_warning = mocker.patch.object(install_log, "warning")
    assert validate_install_configuration(
        {"setup": {"codecov_url": "http://codecov.company.com"}}
    ) == {"setup": {"codecov_url": "http://codecov.company.com"}}
    assert mock_warning.call_count == 0


def test_validate_install_configuration_invalid(mocker):
    mock_warning = mocker.patch.object(install_log, "warning")
    assert validate_install_configuration(
        {"setup": {"codecov_url": "http://codecov.company.com"}, "gitlab": 1}
    ) == {"setup": {"codecov_url": "http://codecov.company.com"}, "gitlab": 1}
    assert mock_warning.call_count == 1


def test_validate_install_configuration_with_user_yaml(mocker):
    user_input = {
        "setup": {"codecov_url": "http://codecov.company.com", "guest_access": False},
        "site": {
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
    }
    mock_warning = mocker.patch.object(install_log, "warning")
    assert validate_install_configuration(user_input) == {
        "setup": {"codecov_url": "http://codecov.company.com", "guest_access": False},
        "site": {
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
                "(?s:.*/[^\\/]*\\.pb\\.go)\\Z",
            ],
        },
    }
    assert mock_warning.call_count == 0


def test_validate_sample_production_config(mocker):
    user_input = {
        "services": {
            "external_dependencies_folder": "./external_deps",
            "minio": {
                "host": "minio",
                "access_key_id": "pokemon01_hmac_id",
                "secret_access_key": "pokemon01_hmac_key",
                "verify_ssl": False,
                "iam_auth": False,
                "iam_endpoint": None,
                "hash_key": "aabb72b4a26e49a1a2a41bebaaa6a9aa",
                "bucket": "codecov",
                "periodic_callback_ms": False,
            },
            "google_analytics_key": "UA-63027104-1",
            "chosen_storage": "gcp",
            "celery_broker": "kaploft-memorystore-celery-url",
            "aws": {"resource": "s3", "region_name": "us-east-1"},
            "sentry": {"server_dsn": "pokemon01_worker_sentry_dsn"},
            "stripe": {"api_key": "pokemonuction_services_stripe_api_key"},
            "gcp": {
                "google_credentials_location": "/path/to-credentials/application_default_credentials.json"
            },
            "database_url": "pokemon01_database_url",
            "redis_url": "kaploft-memorystore-url",
            "vsc_cache": {
                "enabled": True,
                "metrics_app": "shared",
                "check_duration": 100,
                "compare_duration": 110,
                "status_duration": 90,
            },
        },
        "site": {
            "codecov": {"require_ci_to_pass": True},
            "coverage": {
                "precision": 2,
                "round": "down",
                "range": "70...100",
                "status": {
                    "project": True,
                    "patch": True,
                    "changes": False,
                    "default_rules": {"flag_coverage_not_uploaded_behavior": "include"},
                },
            },
            "comment": {
                "layout": "reach, diff, flags, files, footer",
                "behavior": "default",
                "show_carryforward_flags": False,
                "require_base": False,
                "require_changes": False,
                "require_head": True,
            },
            "github_checks": {"annotations": True},
            "parsers": {
                "gcov": {
                    "branch_detection": {
                        "conditional": True,
                        "loop": True,
                        "macro": False,
                        "method": False,
                    }
                },
                "javascript": {"enable_partials": False},
            },
        },
        "setup": {
            "segment": {"enabled": True, "key": "pokemonuction_setup_segment_key"},
            "cache": {"uploads": 86400},
            "codecov_url": "https://codecov.io",
            "debug": False,
            "http": {"force_https": True, "timeouts": {"connect": 30, "receive": 60}},
            "loglvl": "INFO",
            "media": {
                "assets": "https://codecov-cdn.storage.googleapis.com/4.4.8-e33f298",
                "dependancies": "https://codecov-cdn.storage.googleapis.com/4.4.8-e33f298",
            },
            "tasks": {
                "celery": {
                    "hard_timelimit": 240,
                    "soft_timelimit": 200,
                    "enterprise": {"hard_timelimit": 400, "soft_timelimit": 500},
                },
                "upload": {
                    "queue": "uploads",
                    "enterprise": {"hard_timelimit": 400, "soft_timelimit": 500},
                },
                "label_analysis": {
                    "queue": "labelanalysis",
                    "enterprise": {"hard_timelimit": 401, "soft_timelimit": 501},
                },
                "notify": {"queue": "notify", "timeout": 60},
            },
            "encryption_secret": "encryption_$ecret",
        },
        "bitbucket": {
            "bot": {
                "username": "codecov-io",
                "secret": "pokemonuction_bitbucket_bot_secret",
                "key": "pokemonuction_bitbucket_bot_key",
            },
            "client_id": "pokemonuction_bitbucket_client_id",
            "client_secret": "pokemonuction_bitbucket_client_secret",
        },
        "github": {
            "bot": {"username": "codecov-io", "key": "pokemonuction_github_bot_key"},
            "bots": {
                "comment": {
                    "username": "codecov-commenter",
                    "key": "pokemonuction_github_commenter_pa_token",
                },
                "read": {
                    "username": "codecov-commenter",
                    "key": "pokemonuction_github_commenter_pa_token",
                },
                "status": {
                    "username": "codecov-commenter",
                    "key": "pokemonuction_github_commenter_pa_token",
                },
                "tokenless": {
                    "username": "codecov-commenter",
                    "key": "pokemonuction_github_commenter_pa_token",
                },
            },
            "integration": {"id": 254, "pem": "/secrets/github-pem/github.pem"},
        },
        "gitlab": {
            "bot": {"username": "codecov-io", "key": "pokemonuction_gitlab_bot_key"},
        },
    }
    expected_result = {
        "services": {
            "external_dependencies_folder": "./external_deps",
            "minio": {
                "host": "minio",
                "access_key_id": "pokemon01_hmac_id",
                "secret_access_key": "pokemon01_hmac_key",
                "verify_ssl": False,
                "iam_auth": False,
                "iam_endpoint": None,
                "hash_key": "aabb72b4a26e49a1a2a41bebaaa6a9aa",
                "bucket": "codecov",
                "periodic_callback_ms": False,
            },
            "google_analytics_key": "UA-63027104-1",
            "chosen_storage": "gcp",
            "celery_broker": "kaploft-memorystore-celery-url",
            "aws": {"resource": "s3", "region_name": "us-east-1"},
            "sentry": {"server_dsn": "pokemon01_worker_sentry_dsn"},
            "stripe": {"api_key": "pokemonuction_services_stripe_api_key"},
            "gcp": {
                "google_credentials_location": "/path/to-credentials/application_default_credentials.json"
            },
            "database_url": "pokemon01_database_url",
            "redis_url": "kaploft-memorystore-url",
            "vsc_cache": {
                "enabled": True,
                "metrics_app": "shared",
                "check_duration": 100,
                "compare_duration": 110,
                "status_duration": 90,
            },
        },
        "site": {
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
                "layout": "reach, diff, flags, files, footer",
                "behavior": "default",
                "show_carryforward_flags": False,
                "require_base": False,
                "require_changes": False,
                "require_head": True,
            },
            "github_checks": {"annotations": True},
            "parsers": {
                "gcov": {
                    "branch_detection": {
                        "conditional": True,
                        "loop": True,
                        "macro": False,
                        "method": False,
                    }
                },
                "javascript": {"enable_partials": False},
            },
        },
        "setup": {
            "segment": {"enabled": True, "key": "pokemonuction_setup_segment_key"},
            "cache": {"uploads": 86400},
            "codecov_url": "https://codecov.io",
            "debug": False,
            "http": {"force_https": True, "timeouts": {"connect": 30, "receive": 60}},
            "loglvl": "INFO",
            "media": {
                "assets": "https://codecov-cdn.storage.googleapis.com/4.4.8-e33f298",
                "dependancies": "https://codecov-cdn.storage.googleapis.com/4.4.8-e33f298",
            },
            "tasks": {
                "celery": {
                    "hard_timelimit": 240,
                    "soft_timelimit": 200,
                    "enterprise": {"hard_timelimit": 400, "soft_timelimit": 500},
                },
                "label_analysis": {
                    "queue": "labelanalysis",
                    "enterprise": {"hard_timelimit": 401, "soft_timelimit": 501},
                },
                "upload": {
                    "queue": "uploads",
                    "enterprise": {"hard_timelimit": 400, "soft_timelimit": 500},
                },
                "notify": {"queue": "notify", "timeout": 60},
            },
            "encryption_secret": "encryption_$ecret",
        },
        "bitbucket": {
            "bot": {
                "username": "codecov-io",
                "secret": "pokemonuction_bitbucket_bot_secret",
                "key": "pokemonuction_bitbucket_bot_key",
            },
            "client_id": "pokemonuction_bitbucket_client_id",
            "client_secret": "pokemonuction_bitbucket_client_secret",
        },
        "github": {
            "bot": {"username": "codecov-io", "key": "pokemonuction_github_bot_key"},
            "bots": {
                "comment": {
                    "username": "codecov-commenter",
                    "key": "pokemonuction_github_commenter_pa_token",
                },
                "read": {
                    "username": "codecov-commenter",
                    "key": "pokemonuction_github_commenter_pa_token",
                },
                "status": {
                    "username": "codecov-commenter",
                    "key": "pokemonuction_github_commenter_pa_token",
                },
                "tokenless": {
                    "username": "codecov-commenter",
                    "key": "pokemonuction_github_commenter_pa_token",
                },
            },
            "integration": {"id": 254, "pem": "/secrets/github-pem/github.pem"},
        },
        "gitlab": {
            "bot": {"username": "codecov-io", "key": "pokemonuction_gitlab_bot_key"},
        },
    }
    mock_warning = mocker.patch.object(install_log, "warning")
    res = validate_install_configuration(user_input)
    assert mock_warning.call_count == 0
    assert res["site"] == expected_result["site"]
    assert res == expected_result


def test_validate_install_configuration_with_user_yaml_with_user_secret(mocker):
    value = "github/11934774/154468867/https://hooks.slack.com/services/first_key/BE7FWCVHV/dkbfscprianc7wrb"
    encoded_value = UserGivenSecret.encode(value)
    user_yaml_dict = {
        "coverage": {
            "round": "down",
            "precision": 2,
            "range": [70.0, 100.0],
            "status": {"project": {"default": {"base": "auto"}}},
            "notify": {"irc": {"user_given_title": {"password": encoded_value}}},
        },
        "ignore": ["Pods/.*"],
    }
    user_input = {
        "setup": {"codecov_url": "http://codecov.company.com"},
        "site": user_yaml_dict,
    }
    mock_warning = mocker.patch.object(install_log, "warning")
    assert validate_install_configuration(user_input) == {
        "setup": {"codecov_url": "http://codecov.company.com"},
        "site": user_yaml_dict,
    }
    assert mock_warning.call_count == 0


def test_validate_install_configuration_with_additional_yamls(mocker):
    mock_warning = mocker.patch.object(install_log, "warning")
    assert validate_install_configuration(
        {
            "setup": {"codecov_url": "http://codecov.company.com"},
            "additional_user_yamls": [
                {
                    "percentage": 30,
                    "name": "banana",
                    "override": {"comment": False},
                }
            ],
        }
    ) == {
        "setup": {"codecov_url": "http://codecov.company.com"},
        "additional_user_yamls": [
            {
                "percentage": 30,
                "name": "banana",
                "override": {"comment": False},
            }
        ],
    }
    assert mock_warning.call_count == 0


def test_pubsub_config(mocker):
    mock_warning = mocker.patch.object(install_log, "warning")
    assert validate_install_configuration(
        {
            "setup": {
                "pubsub": {
                    "project_id": "1234",
                    "topic": "codecov",
                    "enabled": True,
                }
            },
        }
    ) == {
        "setup": {
            "pubsub": {
                "project_id": "1234",
                "topic": "codecov",
                "enabled": True,
            }
        },
    }
    assert mock_warning.call_count == 0


def test_admins(mocker):
    user_input = {
        "setup": {
            "admins": [
                {
                    "service": "github",
                    "username": "user123",
                }
            ],
        },
    }
    expected_result = {
        "setup": {
            "admins": [
                {
                    "service": "github",
                    "username": "user123",
                }
            ],
        },
    }
    mock_warning = mocker.patch.object(install_log, "warning")
    res = validate_install_configuration(user_input)
    assert mock_warning.call_count == 0
    assert res == expected_result


def test_validate_install_configuration_raise_warning(mocker):
    mock_warning = mocker.patch.object(install_log, "warning")
    input = {
        "setup": {
            "tasks": {
                "celery": {
                    "hard_timelimit": 240,
                    "soft_timelimit": 200,
                    "enterprise": {"hard_timelimit": 400, "soft_timelimit": 500},
                },
                "upload": {"queue": "uploads", "unknown_key": "error"},
                "notify": {"queue": "notify", "timeout": 60},
                "unknown_task": {"queue": "error"},
            }
        }
    }
    validate_install_configuration(input)
    mock_warning.assert_called_with(
        "Configuration considered invalid, using dict as it is",
        extra={
            "errors": {
                "setup": [
                    {
                        "tasks": [
                            {
                                "unknown_task": ["Not a valid TaskConfigGroup"],
                                "upload": [
                                    "none or more than one rule validate",
                                    {
                                        "oneof definition 0": [
                                            {"unknown_key": ["unknown field"]}
                                        ],
                                        "oneof definition 1": [
                                            {
                                                "queue": ["unknown field"],
                                                "unknown_key": ["unknown field"],
                                            }
                                        ],
                                    },
                                ],
                            }
                        ]
                    }
                ]
            }
        },
    )
