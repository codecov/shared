from urllib.parse import urlparse

import django_prometheus

from shared.config import get_config

db_url = get_config("services", "database_url")
if db_url:
    db_conf = urlparse(db_url)
    DATABASE_USER = db_conf.username
    DATABASE_NAME = db_conf.path.replace("/", "")
    DATABASE_PASSWORD = db_conf.password
    DATABASE_HOST = db_conf.hostname
    DATABASE_PORT = db_conf.port
else:
    DATABASE_USER = get_config("services", "database", "username", default="postgres")
    DATABASE_NAME = get_config("services", "database", "name", default="postgres")
    DATABASE_PASSWORD = get_config(
        "services", "database", "password", default="postgres"
    )
    DATABASE_HOST = get_config("services", "database", "host", default="postgres")
    DATABASE_PORT = get_config("services", "database", "port", default=5432)

DATABASE_READ_REPLICA_ENABLED = get_config(
    "setup", "database", "read_replica_enabled", default=False
)

db_read_url = get_config("services", "database_read_url")
if db_read_url:
    db_conf = urlparse(db_read_url)
    DATABASE_READ_USER = db_conf.username
    DATABASE_READ_NAME = db_conf.path.replace("/", "")
    DATABASE_READ_PASSWORD = db_conf.password
    DATABASE_READ_HOST = db_conf.hostname
    DATABASE_READ_PORT = db_conf.port
else:
    DATABASE_READ_USER = get_config(
        "services", "database_read", "username", default="postgres"
    )
    DATABASE_READ_NAME = get_config(
        "services", "database_read", "name", default="postgres"
    )
    DATABASE_READ_PASSWORD = get_config(
        "services", "database_read", "password", default="postgres"
    )
    DATABASE_READ_HOST = get_config(
        "services", "database_read", "host", default="postgres"
    )
    DATABASE_READ_PORT = get_config("services", "database_read", "port", default=5432)

TIMESERIES_ENABLED = get_config("setup", "timeseries", "enabled", default=False)
TIMESERIES_REAL_TIME_AGGREGATES = get_config(
    "setup", "timeseries", "real_time_aggregates", default=False
)

timeseries_database_url = get_config("services", "timeseries_database_url")
if timeseries_database_url:
    timeseries_database_conf = urlparse(timeseries_database_url)
    TIMESERIES_DATABASE_USER = timeseries_database_conf.username
    TIMESERIES_DATABASE_NAME = timeseries_database_conf.path.replace("/", "")
    TIMESERIES_DATABASE_PASSWORD = timeseries_database_conf.password
    TIMESERIES_DATABASE_HOST = timeseries_database_conf.hostname
    TIMESERIES_DATABASE_PORT = timeseries_database_conf.port
else:
    TIMESERIES_DATABASE_USER = get_config(
        "services", "timeseries_database", "username", default="postgres"
    )
    TIMESERIES_DATABASE_NAME = get_config(
        "services", "timeseries_database", "name", default="postgres"
    )
    TIMESERIES_DATABASE_PASSWORD = get_config(
        "services", "timeseries_database", "password", default="postgres"
    )
    TIMESERIES_DATABASE_HOST = get_config(
        "services", "timeseries_database", "host", default="timescale"
    )
    TIMESERIES_DATABASE_PORT = get_config(
        "services", "timeseries_database", "port", default=5432
    )

TIMESERIES_DATABASE_READ_REPLICA_ENABLED = get_config(
    "setup", "timeseries", "read_replica_enabled", default=False
)

timeseries_database_read_url = get_config("services", "timeseries_database_read_url")
if timeseries_database_read_url:
    timeseries_database_conf = urlparse(timeseries_database_read_url)
    TIMESERIES_DATABASE_READ_USER = timeseries_database_conf.username
    TIMESERIES_DATABASE_READ_NAME = timeseries_database_conf.path.replace("/", "")
    TIMESERIES_DATABASE_READ_PASSWORD = timeseries_database_conf.password
    TIMESERIES_DATABASE_READ_HOST = timeseries_database_conf.hostname
    TIMESERIES_DATABASE_READ_PORT = timeseries_database_conf.port
else:
    TIMESERIES_DATABASE_READ_USER = get_config(
        "services", "timeseries_database_read", "username", default="postgres"
    )
    TIMESERIES_DATABASE_READ_NAME = get_config(
        "services", "timeseries_database_read", "name", default="postgres"
    )
    TIMESERIES_DATABASE_READ_PASSWORD = get_config(
        "services", "timeseries_database_read", "password", default="postgres"
    )
    TIMESERIES_DATABASE_READ_HOST = get_config(
        "services", "timeseries_database_read", "host", default="timescale"
    )
    TIMESERIES_DATABASE_READ_PORT = get_config(
        "services", "timeseries_database_read", "port", default=5432
    )

# this is the time in seconds django decides to keep the connection open after the request
# the default is 0 seconds, meaning django closes the connection after every request
# https://docs.djangoproject.com/en/3.1/ref/settings/#conn-max-age
CONN_MAX_AGE = int(get_config("services", "database", "conn_max_age", default=0))

DATABASES = {
    "default": {
        "ENGINE": "psqlextra.backend",
        "NAME": DATABASE_NAME,
        "USER": DATABASE_USER,
        "PASSWORD": DATABASE_PASSWORD,
        "HOST": DATABASE_HOST,
        "PORT": DATABASE_PORT,
        "CONN_MAX_AGE": CONN_MAX_AGE,
    }
}

if DATABASE_READ_REPLICA_ENABLED:
    DATABASES["default_read"] = {
        "ENGINE": "psqlextra.backend",
        "NAME": DATABASE_READ_NAME,
        "USER": DATABASE_READ_USER,
        "PASSWORD": DATABASE_READ_PASSWORD,
        "HOST": DATABASE_READ_HOST,
        "PORT": DATABASE_READ_PORT,
        "CONN_MAX_AGE": CONN_MAX_AGE,
    }

if TIMESERIES_ENABLED:
    DATABASES["timeseries"] = {
        "ENGINE": "django_prometheus.db.backends.postgresql",
        "NAME": TIMESERIES_DATABASE_NAME,
        "USER": TIMESERIES_DATABASE_USER,
        "PASSWORD": TIMESERIES_DATABASE_PASSWORD,
        "HOST": TIMESERIES_DATABASE_HOST,
        "PORT": TIMESERIES_DATABASE_PORT,
        "CONN_MAX_AGE": CONN_MAX_AGE,
    }

    if TIMESERIES_DATABASE_READ_REPLICA_ENABLED:
        DATABASES["timeseries_read"] = {
            "ENGINE": "django_prometheus.db.backends.postgresql",
            "NAME": TIMESERIES_DATABASE_READ_NAME,
            "USER": TIMESERIES_DATABASE_READ_USER,
            "PASSWORD": TIMESERIES_DATABASE_READ_PASSWORD,
            "HOST": TIMESERIES_DATABASE_READ_HOST,
            "PORT": TIMESERIES_DATABASE_READ_PORT,
            "CONN_MAX_AGE": CONN_MAX_AGE,
        }

# See https://django-postgres-extra.readthedocs.io/en/main/settings.html
POSTGRES_EXTRA_DB_BACKEND_BASE: "django_prometheus.db.backends.postgresql"  # type: ignore

# Allows to use the pgpartition command
PSQLEXTRA_PARTITIONING_MANAGER = (
    "shared.django_apps.user_measurements.partitioning.manager"
)

DATABASE_ROUTERS = [
    "shared.django_apps.db_routers.MultiDatabaseRouter",
]

AUTH_USER_MODEL = "codecov_auth.User"
