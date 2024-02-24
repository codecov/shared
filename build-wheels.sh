#!/bin/bash
set -ex

cd /io

for PYBIN in /opt/python/cp{35,36,37,38,39}*/bin; do
    "${PYBIN}/pip" install -U setuptools wheel
    "${PYBIN}/python" setup.py bdist_wheel
done

for whl in dist/*.whl; do
    auditwheel repair "$whl" -w dist/
done
