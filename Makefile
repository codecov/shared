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
	pip install -Iv ruff

lint.run:
	ruff check
	ruff format

lint.check:
	echo "Linting..."
	ruff check
	echo "Formatting..."
	ruff format --check

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
	docker-compose exec shared sh -c 'git fetch --no-tags --prune --depth=1 origin main:refs/remotes/origin/main'
	docker-compose exec shared sh -c 'git diff origin/main ${full_sha} > data.patch'
	docker-compose exec shared sh -c 'pip install mutmut[patch]'
	docker-compose exec shared sh -c 'mutmut run --use-patch-file data.patch || true'
	docker-compose exec shared sh -c 'mkdir /tmp/artifacts;'
	docker-compose exec shared sh -c 'mutmut junitxml > /tmp/artifacts/mut.xml'

test_env.build:
	docker-compose build

test_env.up:
	docker-compose up -d

test_env.test:
	docker-compose exec shared python -m pytest --cov=./ --junitxml=junit.xml
