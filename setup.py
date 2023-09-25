from codecs import open
from os import path

from setuptools import find_packages, setup
from setuptools_rust import Binding, RustExtension

here = path.abspath(path.dirname(__file__))

with open(path.join(here, "README.md"), encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="shared",
    version="0.11.2",
    rust_extensions=[RustExtension("shared.rustyribs", binding=Binding.PyO3)],
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
        "cryptography>=35.0.0",
        "google-cloud-storage>=2.10.0",
        "minio~=7.0",
        "oauth2",
        "protobuf>=4.21.6",
        "tlslite-ng",
        "statsd>=3.3.0",
        "analytics-python==1.3.0b1",
        "httpx>=0.23.0",
        "oauthlib",
        "redis",
        "typing",
        "mmh3",
        "typing_extensions",
        "google-auth>=2.21.0",
        "google-cloud-pubsub>=2.13.6",
        "pytz",
    ],
)
