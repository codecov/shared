CODECOV_UPLOAD_TOKEN ?= "notset"
CODECOV_URL ?= "https://api.codecov.io"
CODECOV_FLAG ?= ""
full_sha := $(shell git rev-parse HEAD)
export CODECOV_TOKEN=${CODECOV_UPLOAD_TOKEN}
.ONESHELL:

test:
	. venv/bin/activate
	python -m pytest --cov=./

lint:
	make lint.install
	make lint.run

lint.install:
	echo "Installing..."
	pip install -Iv black==22.3.0 isort

lint.run:
	black .
	isort --profile black .

lint.check:
	echo "Linting..."
	black --check .
	echo "Sorting..."
	isort --profile black --check .

requirements.install:
	python -m venv venv
	. venv/bin/activate
	pip install -r tests/requirements.txt
	pip install -r requirements.txt
	python setup.py develop
	pip install codecov-cli

test_env.install_cli:
	pip install codecov-cli

test_env.mutation:
	. venv/bin/activate
	git diff origin/main ${full_sha} > data.patch
	pip install mutmut[patch]
	mutmut run --use-patch-file data.patch || true
	mkdir /tmp/artifacts;
	mutmut junitxml > /tmp/artifacts/mut.xml
