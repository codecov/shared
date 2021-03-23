from setuptools import setup, find_packages
from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))

with open(path.join(here, "README.md"), encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="shared",
    version="0.5.0",
    description="Shared Codecov",
    long_description=long_description,
    url="https://github.com/codecov/shared",
    author="Codecov",
    author_email="support@codecov.io",
    packages=find_packages(exclude=["contrib", "docs", "tests"]),
    install_requires=[
        "attrs>=17.4.0",
        "boto3>=1.9.218",
        "colour>=0.1.5",
        "cryptography>=2.7",
        "google-cloud-storage>=1.21",
        "htmldom",
        "minio~=6.0",
        "oauth2",
        "schema>=0.7.0",
        "six>=1.11.0",
        "tlslite-ng",
        "tornado",
        "statsd>=3.3.0",
        "pycurl>=7.43.0.5",
        "analytics-python==1.3.0b1",
        "voluptuous>=0.11.7",
        "httpx>=0.16.0",
        "oauthlib",
        "ribs @ git+ssh://git@github.com/codecov/ribs@v0.1.6#egg=ribs",
    ],
)
