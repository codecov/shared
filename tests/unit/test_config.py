import json
import os

import pytest

from shared.config import ConfigHelper, get_config


class TestConfig(object):
    def test_get_config_nothing_user_set(self, mocker):
        mocker.patch.dict(os.environ, {}, clear=True)
        mocker.patch.object(
            ConfigHelper, "load_yaml_file", side_effect=FileNotFoundError()
        )
        this_config = ConfigHelper()
        mocker.patch("shared.config._get_config_instance", return_value=this_config)
        assert (
            get_config("services", "minio", "hash_key")
            == "ab164bf3f7d947f2a0681b215404873e"
        )
        assert get_config("site", "codecov", "require_ci_to_pass") is True
        assert get_config("site", "coverage", "precision") == 2
        assert get_config("site", "coverage", "round") == "down"
        assert get_config("site", "coverage", "range") == [60.0, 80.0]
        assert get_config("site", "coverage", "status", "project") is True
        assert get_config("site", "coverage", "status", "patch") is True
        assert get_config("site", "coverage", "status", "changes") is False
        assert get_config("site", "comment", "layout") == "reach,diff,flags,tree,reach"
        assert get_config("site", "comment", "behavior") == "default"
        assert get_config("services") == {
            "minio": {
                "host": "minio",
                "access_key_id": "codecov-default-key",
                "secret_access_key": "codecov-default-secret",
                "verify_ssl": False,
                "iam_auth": False,
                "iam_endpoint": None,
                "hash_key": "ab164bf3f7d947f2a0681b215404873e",
            },
            "database_url": "postgresql://postgres:@postgres:5432/postgres",
        }
        assert get_config("setup", "segment", "enabled") is False
        assert (
            get_config("setup", "segment", "key") == "JustARandomTestValueMeaningless"
        )
        assert get_config("setup", "timeseries", "enabled") is False

    def test_get_config_production_use_case(self, mocker):
        yaml_content = "\n".join(
            [
                "setup:",
                "  codecov_url: https://codecov.io",
                "",
                "  segment:",
                "    enabled: True",
                "    key: '123'",
                "  debug: no",
                "  loglvl: INFO",
                "  media:",
                "    assets: assets_link",
                "    dependancies: assets_link",
                "  http:",
                "    force_https: yes",
                "    timeouts:",
                "      connect: 10",
                "      receive: 15",
                "  tasks:",
                "    celery:",
                "      soft_timelimit: 200",
                "      hard_timelimit: 240",
                "    upload:",
                "      queue: uploads",
                "  cache:",
                "    yaml: 600  # 10 minutes",
                "    tree: 600  # 10 minutes",
                "    diff: 300  # 5 minutes",
                "    chunks: 300  # 5 minutes",
                "    uploads: 86400  # 1 day",
                "",
                "services:",
                "  minio:",
                "    bucket: codecov",
                "    periodic_callback_ms: false",
                "  sentry:",
                "    server_dsn: server_dsn",
                "  google_analytics_key: UA-google_analytics_key-1",
                "",
                "github:",
                "  bot:",
                "    username: codecov-io",
                "  integration:",
                "    id: 254",
                "    pem: src/certs/github.pem",
                "",
                "bitbucket:",
                "  bot:",
                "    username: codecov-io",
                "",
                "gitlab:",
                "  bot:",
                "    username: codecov-io",
                "",
                "site:",
                "  codecov:",
                "    require_ci_to_pass: yes",
                "",
                "  coverage:",
                "    precision: 2",
                "    round: down",
                "    range: '70...100'",
                "",
                "    status:",
                "      project: yes",
                "      patch: yes",
                "      changes: no",
                "",
                "  parsers:",
                "    gcov:",
                "      branch_detection:",
                "        conditional: yes",
                "        loop: yes",
                "        method: no",
                "        macro: no",
                "",
                "    javascript:",
                "      enable_partials: no",
                "",
                "  comment:",
                "    layout: 'reach, diff, flags, files, footer'",
                "    behavior: default",
                "    require_changes: no",
                "    require_base: no",
                "    require_head: yes",
            ]
        )
        mocker.patch.object(ConfigHelper, "load_yaml_file", return_value=yaml_content)
        this_config = ConfigHelper()
        mocker.patch("shared.config._get_config_instance", return_value=this_config)
        assert get_config("site", "codecov", "require_ci_to_pass") is True
        assert get_config("site", "coverage", "precision") == 2
        assert get_config("site", "coverage", "round") == "down"
        assert get_config("site", "coverage", "range") == [70.0, 100.0]
        assert get_config("site", "coverage", "status", "project") is True
        assert get_config("site", "coverage", "status", "patch") is True
        assert get_config("site", "coverage", "status", "changes") is False
        assert (
            get_config(
                "site",
                "coverage",
                "status",
                "default_rules",
                "flag_coverage_not_uploaded_behavior",
            )
            == "include"
        )
        assert [
            x.strip() for x in get_config("site", "comment", "layout").split(",")
        ] == ["reach", "diff", "flags", "files", "footer"]
        assert get_config("site", "comment", "behavior") == "default"
        assert get_config("site", "comment", "show_carryforward_flags") is False
        assert get_config("setup", "segment", "enabled") is True
        assert get_config("setup", "segment", "key") == "123"

    def test_get_config_case_with_more_nested_types(self, mocker):
        yaml_content = "\n".join(
            [
                "setup:",
                "  codecov_url: https://codecov.io",
                "",
                "  debug: no",
                "  loglvl: INFO",
                "  media:",
                "    assets: assets_link",
                "    dependancies: assets_link",
                "  http:",
                "    force_https: yes",
                "    timeouts:",
                "      connect: 10",
                "      receive: 15",
                "  tasks:",
                "    celery:",
                "      soft_timelimit: 200",
                "      hard_timelimit: 240",
                "    upload:",
                "      queue: uploads",
                "  cache:",
                "    yaml: 600  # 10 minutes",
                "    tree: 600  # 10 minutes",
                "    diff: 300  # 5 minutes",
                "    chunks: 300  # 5 minutes",
                "    uploads: 86400  # 1 day",
                "",
                "services:",
                "  minio:",
                "    bucket: codecov",
                "    periodic_callback_ms: false",
                "  sentry:",
                "    server_dsn: server_dsn",
                "  google_analytics_key: UA-google_analytics_key-1",
                "",
                "github:",
                "  bot:",
                "    username: codecov-io",
                "  integration:",
                "    id: 254",
                "    pem: src/certs/github.pem",
                "",
                "bitbucket:",
                "  bot:",
                "    username: codecov-io",
                "",
                "gitlab:",
                "  bot:",
                "    username: codecov-io",
                "",
                "site:",
                "  codecov:",
                "    require_ci_to_pass: yes",
                "",
                "    status:",
                "      project: yes",
                "      patch: yes",
                "      changes: no",
                "",
                "  parsers:",
                "    gcov:",
                "      branch_detection:",
                "        conditional: yes",
                "        loop: yes",
                "        method: no",
                "        macro: no",
                "",
                "    javascript:",
                "      enable_partials: no",
                "",
                "  coverage:",
                "    status:",
                "      project:",
                "        default:",
                "          only_pulls: true",
                "          target: auto",
                "          threshold: 100%",
                "      patch:",
                "        default:",
                "          only_pulls: true",
                "          target: auto",
                "          threshold: 100%",
            ]
        )
        mocker.patch.object(ConfigHelper, "load_yaml_file", return_value=yaml_content)
        this_config = ConfigHelper()
        mocker.patch("shared.config._get_config_instance", return_value=this_config)
        assert get_config("site", "codecov", "require_ci_to_pass") is True
        assert get_config("site", "coverage", "precision") == 2
        assert get_config("site", "coverage", "round") == "down"
        assert get_config("site", "coverage", "range") == [60, 80]
        assert get_config("site", "coverage", "status") == {
            "project": {
                "default": {"only_pulls": True, "target": "auto", "threshold": 100.0}
            },
            "patch": {
                "default": {"only_pulls": True, "target": "auto", "threshold": 100.0}
            },
            "changes": False,
            "default_rules": {"flag_coverage_not_uploaded_behavior": "include"},
        }
        assert get_config("site", "coverage", "status", "project") == {
            "default": {"only_pulls": True, "target": "auto", "threshold": 100.0}
        }
        assert get_config("site", "coverage", "status", "patch") == {
            "default": {"only_pulls": True, "target": "auto", "threshold": 100.0}
        }
        assert get_config("site", "coverage", "status", "changes") is False
        assert [
            x.strip() for x in get_config("site", "comment", "layout").split(",")
        ] == ["reach", "diff", "flags", "tree", "reach"]
        assert get_config("site", "comment", "behavior") == "default"
        assert get_config("site", "comment", "show_carryforward_flags") is False

    def test_get_config_minio_without_port(self, mocker):
        yaml_content = "\n".join(
            [
                "services:",
                "  minio:",
                "    host: s3.amazonaws.com",
                "    bucket: cce-minio-update-test",
                "    region: us-east-2",
                "    verify_ssl: true",
                "    iam_auth: true",
            ]
        )
        mocker.patch.object(ConfigHelper, "load_yaml_file", return_value=yaml_content)
        this_config = ConfigHelper()
        mocker.patch("shared.config._get_config_instance", return_value=this_config)
        assert get_config("services", "minio") == {
            "host": "s3.amazonaws.com",
            "access_key_id": "codecov-default-key",
            "secret_access_key": "codecov-default-secret",
            "verify_ssl": True,
            "iam_auth": True,
            "iam_endpoint": None,
            "bucket": "cce-minio-update-test",
            "region": "us-east-2",
            "hash_key": "ab164bf3f7d947f2a0681b215404873e",
        }

    def test_get_config_minio_with_port(self, mocker):
        yaml_content = "\n".join(
            [
                "services:",
                "  minio:",
                "    host: s3.amazonaws.com",
                "    port: 9000",
                "    bucket: cce-minio-update-test",
                "    region: us-east-2",
                "    verify_ssl: true",
                "    iam_auth: true",
            ]
        )
        mocker.patch.object(ConfigHelper, "load_yaml_file", return_value=yaml_content)
        this_config = ConfigHelper()
        mocker.patch("shared.config._get_config_instance", return_value=this_config)
        assert get_config("services", "minio") == {
            "host": "s3.amazonaws.com",
            "port": 9000,
            "access_key_id": "codecov-default-key",
            "secret_access_key": "codecov-default-secret",
            "verify_ssl": True,
            "iam_auth": True,
            "iam_endpoint": None,
            "bucket": "cce-minio-update-test",
            "region": "us-east-2",
            "hash_key": "ab164bf3f7d947f2a0681b215404873e",
        }

    def test_parse_path_and_value_from_envvar(self, mocker):
        this_config = ConfigHelper()
        mock_env = {
            "CONVERT__TO__BOOL__TRUE1": ("true", True),
            "CONVERT__TO__BOOL__TRUE2": ("True", True),
            "CONVERT__TO__BOOL__TRUE3": ("TRUE", True),
            "CONVERT__TO__BOOL__TRUE4": ("on", True),
            "CONVERT__TO__BOOL__TRUE5": ("On", True),
            "CONVERT__TO__BOOL__TRUE6": ("ON", True),
            "CONVERT__TO__BOOL__FALSE1": ("false", False),
            "CONVERT__TO__BOOL__FALSE2": ("False", False),
            "CONVERT__TO__BOOL__FALSE3": ("FALSE", False),
            "CONVERT__TO__BOOL__FALSE4": ("off", False),
            "CONVERT__TO__BOOL__FALSE5": ("Off", False),
            "CONVERT__TO__BOOL__FALSE6": ("OFF", False),
            "CONVERT__TO__INT__123": ("123", 123),
            "CONVERT__TO__INT__-123": ("-123", -123),
            "CONVERT__TO__FLOAT__12.3": ("12.3", 12.3),
            "CONVERT__TO__FLOAT__-12.3": ("-12.3", -12.3),
            "LEAVE__ALONE__MALFORMED__TRUE1": ("TrUe", "TrUe"),
            "LEAVE__ALONE__MALFORMED__TRUE2": ("oN", "oN"),
            "LEAVE__ALONE__MALFORMED__FALSE1": ("FaLse", "FaLse"),
            "LEAVE__ALONE__MALFORMED__FALSE2": ("oFF", "oFF"),
            "LEAVE__ALONE__MALFORMED__FLOAT": ("12.3.4", "12.3.4"),
            "LEAVE__ALONE__STRING": ("hello world", "hello world"),
        }

        mocker.patch.dict(
            os.environ,
            {k: v[0] for k, v in mock_env.items()},
        )

        for k, v in mock_env.items():
            expected_path = k.split("__")
            env_val, expected_val = v
            assert this_config._parse_path_and_value_from_envvar(k) == (
                expected_path,
                expected_val,
            )

    def test_load_env_var(self, mocker):
        this_config = ConfigHelper()
        mocker.patch.dict(
            os.environ,
            {
                "SERVICES__MINIO__HASH_KEY": "hash_key",
                "SERVICES__CHOSEN_STORAGE": "gcp_with_fallback",
                "SERVICES__CELERY_BROKER": "broker_url",
                "SETUP__ENCRYPTION_SECRET": "secret",
                "GITHUB__BOT__KEY": "GITHUB__BOT__KEY",
                "SERVICES__AWS__RESOURCE": "s3",
                "SERVICES__SENTRY__SERVER_DSN": "dsn",
                "SETUP__TASKS__STATUS__QUEUE": "new_tasks",
                "SERVICES__MINIO__HOST": "minio-proxy",
                "BITBUCKET__BOT__SECRET": "BITBUCKET__BOT__SECRET",
                "SERVICES__STRIPE__API_KEY": "SERVICES__STRIPE__API_KEY",
                "SERVICES__AWS__AWS_ACCESS_KEY_ID": "SERVICES__AWS__AWS_ACCESS_KEY_ID",
                "SERVICES__MINIO__PORT": "9000",
                "SERVICES__AWS__AWS_SECRET_ACCESS_KEY": "1/SERVICES__AWS__AWS_SECRET_ACCESS_KEY",
                "BITBUCKET__CLIENT_ID": "BITBUCKET__CLIENT_ID",
                "BITBUCKET__CLIENT_SECRET": "BITBUCKET__CLIENT_SECRET",
                "SERVICES__GCP__GOOGLE_CREDENTIALS_LOCATION": "/secret/gcs-credentials/path.json",
                "GITHUB__INTEGRATION__PEM": "/secrets/github-pem/github.pem",
                "SERVICES__DATABASE_URL": "postgresql://user:pass@127.0.0.1:5432/postgres",
                "SERVICES__TIMESERIES_DATABASE_URL": "postgresql://user:pass@timescale:5432/timescale",
                "BITBUCKET__BOT__KEY": "BITBUCKET__BOT__KEY",
                "SERVICES__MINIO__ACCESS_KEY_ID": "SERVICES__MINIO__ACCESS_KEY_ID",
                "SERVICES__MINIO__SECRET_ACCESS_KEY": "SERVICES__MINIO__SECRET_ACCESS_KEY",
                "GITLAB__BOT__KEY": "GITLAB__BOT__KEY",
                "SERVICES__REDIS_URL": "SERVICES__REDIS_URL:11234",
                "SERVICES__AWS__REGION_NAME": "us-east-1",
                "SENTRY_PERCENTAGE": "0.9",
                "__BAD__KEY": "GITLAB__BOT__KEY",
                "SETUP__SEGMENT__ENABLED": "True",
                "SETUP__SEGMENT__KEY": "abc",
                "SETUP__TIMESERIES__ENABLED": "True",
                "JSONCONFIG___SETUP__MEDIA": json.dumps(
                    {"assets": "aaa", "dependancies": "bbb"}
                ),
            },
        )
        expected_res = {
            "services": {
                "minio": {
                    "hash_key": "hash_key",
                    "host": "minio-proxy",
                    "port": 9000,
                    "access_key_id": "SERVICES__MINIO__ACCESS_KEY_ID",
                    "secret_access_key": "SERVICES__MINIO__SECRET_ACCESS_KEY",
                },
                "chosen_storage": "gcp_with_fallback",
                "celery_broker": "broker_url",
                "aws": {
                    "resource": "s3",
                    "aws_access_key_id": "SERVICES__AWS__AWS_ACCESS_KEY_ID",
                    "aws_secret_access_key": "1/SERVICES__AWS__AWS_SECRET_ACCESS_KEY",
                    "region_name": "us-east-1",
                },
                "sentry": {"server_dsn": "dsn"},
                "stripe": {"api_key": "SERVICES__STRIPE__API_KEY"},
                "gcp": {
                    "google_credentials_location": "/secret/gcs-credentials/path.json"
                },
                "database_url": "postgresql://user:pass@127.0.0.1:5432/postgres",
                "timeseries_database_url": "postgresql://user:pass@timescale:5432/timescale",
                "redis_url": "SERVICES__REDIS_URL:11234",
            },
            "setup": {
                "media": {"assets": "aaa", "dependancies": "bbb"},
                "encryption_secret": "secret",
                "tasks": {"status": {"queue": "new_tasks"}},
                "segment": {"enabled": True, "key": "abc"},
                "timeseries": {"enabled": True},
            },
            "github": {
                "bot": {"key": "GITHUB__BOT__KEY"},
                "integration": {"pem": "/secrets/github-pem/github.pem"},
            },
            "bitbucket": {
                "bot": {
                    "secret": "BITBUCKET__BOT__SECRET",
                    "key": "BITBUCKET__BOT__KEY",
                },
                "client_id": "BITBUCKET__CLIENT_ID",
                "client_secret": "BITBUCKET__CLIENT_SECRET",
            },
            "gitlab": {"bot": {"key": "GITLAB__BOT__KEY"}},
        }
        assert expected_res == this_config.load_env_var()

    def test_yaml_content(self, mocker):
        mocker.patch.object(
            ConfigHelper, "load_yaml_file", side_effect=FileNotFoundError()
        )
        this_config = ConfigHelper()
        assert this_config.yaml_content() == {}

    def test_load_filename_from_path_base64(self, mocker):
        mocker.patch.dict(os.environ, {}, clear=True)
        mocker.patch.object(
            ConfigHelper, "load_yaml_file", side_effect=FileNotFoundError()
        )
        this_config = ConfigHelper()
        this_config.set_params(
            {
                "some": {
                    "githubpem": {
                        "source_type": "base64env",
                        "value": "bW9ua2V5YmFuYW5hc29tZXRoaW5nZGFuY2U=",
                    }
                }
            }
        )
        res = this_config.load_filename_from_path("some", "githubpem")
        assert res == "monkeybananasomethingdance"

    def test_load_filename_from_path_inexisting_file_path(self, mocker):
        mocker.patch.dict(os.environ, {}, clear=True)
        mocker.patch.object(
            ConfigHelper, "load_yaml_file", side_effect=FileNotFoundError()
        )
        this_config = ConfigHelper()
        this_config.set_params(
            {
                "some": {
                    "githubpem": {
                        "source_type": "filepath",
                        "value": "inexistent/path/on/purpose.hahaha",
                    }
                }
            }
        )
        with pytest.raises(FileNotFoundError):
            this_config.load_filename_from_path("some", "githubpem")

    def test_load_filename_from_path_existing_file_path(self, mocker, tmpdir):
        p = tmpdir.mkdir("sub").join("hello.txt")
        p.write("This is not a knife")
        mocker.patch.dict(os.environ, {}, clear=True)
        mocker.patch.object(
            ConfigHelper, "load_yaml_file", side_effect=FileNotFoundError()
        )
        this_config = ConfigHelper()
        this_config.set_params(
            {"some": {"githubpem": {"source_type": "filepath", "value": str(p)}}}
        )
        res = this_config.load_filename_from_path("some", "githubpem")
        assert res == "This is not a knife"

    def test_load_filename_from_path_just_using_string_existing_file_path(
        self, mocker, tmpdir
    ):
        mocker.patch.dict(os.environ, {}, clear=True)
        mocker.patch.object(
            ConfigHelper, "load_yaml_file", side_effect=FileNotFoundError()
        )
        p = tmpdir.mkdir("sub").join("hello.txt")
        p.write("This is not a knife. This is a knife")
        this_config = ConfigHelper()
        this_config.set_params({"some": {"githubpem": str(p)}})
        res = this_config.load_filename_from_path("some", "githubpem")
        assert res == "This is not a knife. This is a knife"
