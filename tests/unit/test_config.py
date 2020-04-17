import os

from shared.config import ConfigHelper, get_config


class TestConfig(object):
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
        assert get_config() == {
            "services": {
                "minio": {
                    "host": "s3.amazonaws.com",
                    "access_key_id": "codecov-default-key",
                    "secret_access_key": "codecov-default-secret",
                    "verify_ssl": True,
                    "iam_auth": True,
                    "iam_endpoint": None,
                    "bucket": "cce-minio-update-test",
                    "region": "us-east-2",
                }
            }
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
        assert get_config() == {
            "services": {
                "minio": {
                    "host": "s3.amazonaws.com",
                    "port": 9000,
                    "access_key_id": "codecov-default-key",
                    "secret_access_key": "codecov-default-secret",
                    "verify_ssl": True,
                    "iam_auth": True,
                    "iam_endpoint": None,
                    "bucket": "cce-minio-update-test",
                    "region": "us-east-2",
                }
            }
        }

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
                "SERVICES__DATABASE_URL": "postgres://user:pass@127.0.0.1:5432/postgres",
                "BITBUCKET__BOT__KEY": "BITBUCKET__BOT__KEY",
                "SERVICES__MINIO__ACCESS_KEY_ID": "SERVICES__MINIO__ACCESS_KEY_ID",
                "SERVICES__MINIO__SECRET_ACCESS_KEY": "SERVICES__MINIO__SECRET_ACCESS_KEY",
                "GITLAB__BOT__KEY": "GITLAB__BOT__KEY",
                "SERVICES__REDIS_URL": "SERVICES__REDIS_URL:11234",
                "SERVICES__AWS__REGION_NAME": "us-east-1",
                "SENTRY_PERCENTAGE": "0.9",
                "__BAD__KEY": "GITLAB__BOT__KEY",
            },
        )
        expected_res = {
            "services": {
                "minio": {
                    "hash_key": "hash_key",
                    "host": "minio-proxy",
                    "port": "9000",
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
                "database_url": "postgres://user:pass@127.0.0.1:5432/postgres",
                "redis_url": "SERVICES__REDIS_URL:11234",
            },
            "setup": {
                "encryption_secret": "secret",
                "tasks": {"status": {"queue": "new_tasks"}},
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
        mocker.patch.object(ConfigHelper, "load_yaml_file", side_effect=FileNotFoundError())
        this_config = ConfigHelper()
        assert this_config.yaml_content() == {}
