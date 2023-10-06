#!/bin/bash

python -m venv venv
source venv/bin/activate
pip install setuptools_rust
pip install -r tests/requirements.txt
pip install -r requirements.txt
python setup.py develop
pip install codecov-cli