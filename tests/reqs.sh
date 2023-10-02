#!/bin/bash

curl https://sh.rustup.rs -sSf | sh -s -- -y
source $HOME/.cargo/env
pwd
ls
python3 -m venv venv
ls venv
source venv/bin/activate
pip3 install -r tests/requirements.txt
pip3 install setuptools_rust
python3 setup.py develop
pip3 install codecov-cli