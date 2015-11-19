#!/usr/bin/env python
from setuptools import setup

version = '0.0.1'

setup(name='service-scms',
      version=version,
      description="",
      long_description=None,
      keywords='',
      author='',
      author_email='',
      url='http://github.com/codecov/service-scms',
      license='http://www.apache.org/licenses/LICENSE-2.0',
      packages=['scms'],
      include_package_data=True,
      zip_safe=True,
      install_requires=["requests>=2.0.0", ])
