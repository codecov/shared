#!/usr/bin/env python
from setuptools import setup

version = '0.0.1'

setup(name='torngit',
      version=version,
      description="",
      long_description=None,
      keywords='',
      author='',
      author_email='',
      url='http://github.com/codecov/torngit',
      license='http://www.apache.org/licenses/LICENSE-2.0',
      packages=['torngit'],
      include_package_data=True,
      zip_safe=True,
      install_requires=["requests>=2.0.0", ])
