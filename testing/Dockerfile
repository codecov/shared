FROM            python:3.8.7-alpine3.13

RUN             apk update \
                && apk add --update --no-cache \
                git \
                musl-dev \
                libxslt-dev \
                python3-dev \
                libffi-dev \
                gcc \
                build-base \
                rust \
                cargo \
                && pip install --upgrade pip

RUN             pip install setuptools_rust

WORKDIR         /folder

COPY            .cargo .cargo
COPY            src src
COPY            build-wheels.sh build-wheels.sh
COPY            Cargo.toml Cargo.toml
COPY            MANIFEST.in MANIFEST.in
COPY            pyproject.toml pyproject.toml
COPY            setup.py setup.py
COPY            ribs ribs

RUN             python setup.py install

WORKDIR         /

COPY            testing/loadfile.py loadfile.py

ENTRYPOINT      python loadfile.py