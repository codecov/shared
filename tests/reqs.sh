#!/bin/bash

curl https://sh.rustup.rs -sSf | sh -s -- -y
source $HOME/.cargo/env
python -m venv venv
source venv/bin/activate
pip install -r tests/requirements.txt
pip install setuptools_rust
python setup.py develop
pip install codecov-cli