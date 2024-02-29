CODECOV_UPLOAD_TOKEN ?= "notset"
CODECOV_URL ?= "https://api.codecov.io"
CODECOV_FLAG ?= ""
full_sha := $(shell git rev-parse HEAD)
export CODECOV_TOKEN=${CODECOV_UPLOAD_TOKEN}
.ONESHELL:

test:
	docker compose exec shared python -m pytest --cov=./ 

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

test_env.build:
	docker-compose build

test_env.up:
	docker-compose up -d

test_env.test:
	docker-compose exec shared python -m pytest --cov=./ --junitxml=junit.xml
