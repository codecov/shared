from codecs import open
from os import path

from setuptools import find_packages, setup

here = path.abspath(path.dirname(__file__))

with open(path.join(here, "README.md"), encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="shared",
    version="0.11.2",
    packages=find_packages(exclude=["contrib", "docs", "tests*"]),
    # rust extensions are not zip safe, just like C-extensions.
    zip_safe=False,
    description="Shared Codecov",
    long_description=long_description,
    url="https://github.com/codecov/shared",
    author="Codecov",
    author_email="support@codecov.io",
    install_requires=[
        "boto3>=1.9.218",
        "cerberus",
        "colour>=0.1.5",
        "cryptography>=41.0.6",
        "google-cloud-storage>=2.10.0",
        "minio~=7.0",
        "oauth2",
        "protobuf>=4.21.6",
        "tlslite-ng>=0.8.0b1",
        "statsd>=3.3.0",
        "prometheus-client",
        "analytics-python==1.3.0b1",
        "httpx>=0.23.0",
        "certifi>=2023.07.22",
        "oauthlib",
        "redis",
        "typing",
        "mmh3",
        "typing_extensions",
        "google-auth>=2.21.0",
        "google-cloud-pubsub>=2.13.6",
        "urllib3>=1.25.4,<1.27",
        "pyjwt",
        "pytz",
        "django>=4.2.10,<5.0",  # api uses python 3.9, non-compatible with >5.0
        "sqlalchemy==1.*",
        "ijson==3.*",
        "codecov-ribs",
        "cachetools",
        "django-better-admin-arrayfield",
        # API Deps
        "django-prometheus",
        "django-model-utils",
        "factory-boy",
        "python-redis-lock",
        "django-model-utils==4.3.1",
        "requests==2.31.0",
        "sentry-sdk>=1.40.0",
    ],
)
