from setuptools import setup, find_packages
from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))

with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='covreports',
    version='0.1.0',
    description='Reporting for Codecov',
    long_description=long_description,
    url='https://github.com/codecov/report',
    author='Codecov',
    author_email='support@codecov.io',
    packages=find_packages(exclude=['contrib', 'docs', 'tests']),
    install_requires=[
        "attrs==17.4.0",
        "boto3==1.9.218",
        "colour==0.1.5",
        "coverage==4.5",
        "cryptography==2.7",
        "google-cloud-storage==1.18.0",
        "minio==5.0.8",
        "mock==2.0.0",
        "pycrypto==2.6.1",
        "pytest-cov==2.5.1",
        "pytest-mock==1.10.1",
        "pytest==4.5.0",
        "six==1.11.0",
        "vcrpy==2.1.0",
        "schema==0.7.0"
    ]
)
