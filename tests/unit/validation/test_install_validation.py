from shared.validation.install import validate_install_configuration


def test_validate_install_configuration_empty():
    assert validate_install_configuration({}) == {}


def test_validate_install_configuration_simple():
    assert validate_install_configuration(
        {"setup": {"codecov_url": "http://codecov.company.com"}}
    ) == {"setup": {"codecov_url": "http://codecov.company.com"}}


def test_validate_install_configuration_invalid():
    assert validate_install_configuration(
        {"setup": {"codecov_url": "http://codecov.company.com"}, "gitlab": 1}
    ) == {"setup": {"codecov_url": "http://codecov.company.com"}, "gitlab": 1}


def test_validate_install_configuration_with_user_yaml():
    user_input = {
        "setup": {"codecov_url": "http://codecov.company.com"},
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
    assert validate_install_configuration(user_input) == {
        "setup": {"codecov_url": "http://codecov.company.com"},
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
                "(?s:vendor/.*/[^\\/]+)\\Z",
                "(?s:.*/[^\\/]+\\.pb\\.go.*)\\Z",
            ],
        },
    }


def test_validate_sample_production_config():
    user_input = {
        "services": {
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
            "segment": {"enabled": True, "key": "pokemonuction_setup_segment_key",},
            "cache": {"uploads": 86400,},
            "codecov_url": "https://codecov.io",
            "debug": False,
            "http": {"force_https": True, "timeouts": {"connect": 30, "receive": 60}},
            "loglvl": "INFO",
            "media": {
                "assets": "https://codecov-cdn.storage.googleapis.com/4.4.8-e33f298",
                "dependancies": "https://codecov-cdn.storage.googleapis.com/4.4.8-e33f298",
            },
            "tasks": {
                "celery": {"hard_timelimit": 240, "soft_timelimit": 200},
                "upload": {"queue": "uploads"},
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
            "bot": {"username": "codecov-io", "key": "pokemonuction_github_bot_key",},
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
            },
            "integration": {"id": 254, "pem": "/secrets/github-pem/github.pem"},
        },
        "gitlab": {
            "bot": {"username": "codecov-io", "key": "pokemonuction_gitlab_bot_key",}
        },
    }
    expected_result = {
        "services": {
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
            "segment": {"enabled": True, "key": "pokemonuction_setup_segment_key",},
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
                "celery": {"hard_timelimit": 240, "soft_timelimit": 200},
                "upload": {"queue": "uploads"},
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
            },
            "integration": {"id": 254, "pem": "/secrets/github-pem/github.pem"},
        },
        "gitlab": {
            "bot": {"username": "codecov-io", "key": "pokemonuction_gitlab_bot_key"}
        },
    }
    res = validate_install_configuration(user_input)
    assert res["site"] == expected_result["site"]
    assert res == expected_result
