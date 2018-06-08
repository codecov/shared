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
    url='https://github.com/TomPed/report',
    author='Codecov',
    author_email='support@codecov.io',
    packages=find_packages(exclude=['contrib', 'docs', 'tests']),
)
