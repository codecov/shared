from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent
from shared.django_apps.db_settings import *

ALLOWED_HOSTS = []

# Install apps so that you can make migrations for them
INSTALLED_APPS = [
    "shared.django_apps.pg_telemetry",
    "shared.django_apps.ts_telemetry",
    "shared.django_apps.rollouts",
]

MIDDLEWARE = []

TEMPLATES = []

TELEMETRY_VANILLA_DB = "default"
TELEMETRY_TIMESCALE_DB = "timeseries"

TEST = True

# Database
# https://docs.djangoproject.com/en/4.2/ref/settings/#databases
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
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


# Internationalization
# https://docs.djangoproject.com/en/4.2/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True
