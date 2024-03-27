# syntax=docker/dockerfile:1.4
ARG PYTHON_IMAGE=python:3.11-slim-bullseye

FROM $PYTHON_IMAGE as build

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    libxslt-dev \
    python3-dev \
    libffi-dev \
    libpq-dev \
    gcc \
    bash \
    make \
    build-essential \
    curl \
    && pip install --upgrade pip

WORKDIR /app
COPY . /app

RUN pip install -r tests/requirements.txt && \
    pip install -r requirements.txt && \
    python setup.py develop && \
    pip install codecov-cli
