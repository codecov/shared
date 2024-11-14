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
    package_data={"shared": ["py.typed"]},
    description="Shared Codecov",
    long_description=long_description,
    url="https://github.com/codecov/shared",
    author="Codecov",
    author_email="support@codecov.io",
    python_requires=">=3.12",
    install_requires=[
        "boto3>=1.9.218",
        "cachetools",
        "cerberus",
        "certifi>=2024.07.04",
        "codecov-ribs",
        "colour>=0.1.5",
        "cryptography>=43.0.1",
        "django-better-admin-arrayfield",
        "django-postgres-extra>=2.0.8",
        "django>=4.2.10,<5.0",  # api uses python 3.9, non-compatible with >5.0
        "google-auth>=2.21.0",
        "google-cloud-pubsub>=2.13.6",
        "google-cloud-storage>=2.10.0",
        "httpx>=0.23.0",
        "ijson==3.*",
        "minio~=7.0",
        "mmh3",
        "oauthlib",
        "orjson",
        "prometheus-client",
        "protobuf>=4.21.6",
        "pyjwt",
        "pyparsing",
        "redis",
        "sqlalchemy==1.*",
        "urllib3==1.26.19",
        # API Deps
        "django-model-utils>=4.3.1",
        "django-prometheus",
        "python-redis-lock",
        "requests>=2.32.3",
        "sentry-sdk>=2.13.0",
    ],
)
