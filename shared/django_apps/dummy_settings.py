from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent
from shared.django_apps.db_settings import *

ALLOWED_HOSTS = []

# Install apps so that you can make migrations for them
INSTALLED_APPS = [
    "shared.django_apps.legacy_migrations",
    "shared.django_apps.pg_telemetry",
    "shared.django_apps.ts_telemetry",
    "shared.django_apps.rollouts",
    "shared.django_apps.user_measurements",
    # Needed for makemigrations to work
    "django.contrib.auth",
    "django.contrib.messages",
    # partitions
    "psqlextra",
    "django_prometheus",
    # API models
    "django.contrib.admin",
    "django.contrib.contenttypes",
    "django.contrib.postgres",
    "shared.django_apps.codecov_auth",
    "shared.django_apps.core",
    "shared.django_apps.reports",
]

# Needed for makemigrations to work
MIDDLEWARE = [
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
]

# Needed for makemigrations to work
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.contrib.auth.context_processors.auth",
                "django.template.context_processors.request",
                "django.contrib.messages.context_processors.messages",
            ]
        },
    }
]

TELEMETRY_VANILLA_DB = "default"
TELEMETRY_TIMESCALE_DB = "timeseries"

# Needed for migrations that depend on settings.auth_user_model
AUTH_USER_MODEL = "codecov_auth.User"

# Needed as certain migrations refer to it
SKIP_RISKY_MIGRATION_STEPS = get_config("migrations", "skip_risky_steps", default=False)

TEST = True

# Database
# https://docs.djangoproject.com/en/4.2/ref/settings/#databases
DATABASES = {
    "default": {
        "ENGINE": "psqlextra.backend",
        "NAME": "postgres",
        "USER": "postgres",
        "PASSWORD": "password",
        "HOST": "postgres",
        "PORT": 5432,
    },
    "timeseries": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "postgres",
        "USER": "postgres",
        "PASSWORD": "postgres",
        "HOST": "timescale",
        "PORT": 5432,
    },
}

DATABASE_ROUTERS = [
    "shared.django_apps.db_routers.TelemetryDatabaseRouter",
    "shared.django_apps.db_routers.MultiDatabaseRouter",
]

# Password validation
# https://docs.djangoproject.com/en/4.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = []

# See https://django-postgres-extra.readthedocs.io/en/master/settings.html
POSTGRES_EXTRA_DB_BACKEND_BASE: "django_prometheus.db.backends.postgresql"

# Allows to use the pgpartition command
PSQLEXTRA_PARTITIONING_MANAGER = "user_measurements.partitioning.manager"


# Internationalization
# https://docs.djangoproject.com/en/4.2/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True
