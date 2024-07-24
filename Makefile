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
	ruff check --fix
	echo "Formatting..."
	ruff format --check

requirements.install:
	python -m venv venv
	. venv/bin/activate
	pip install -r tests/requirements.txt
	pip install -r requirements.txt
	python setup.py develop
	pip install codecov-cli==0.7.2

test_env.install_cli:
	pip install codecov-cli==0.7.2

test_env.build:
	docker-compose build

test_env.up:
	docker-compose up -d

test_env.test:
	docker-compose exec shared python -m pytest --cov=./ --junitxml=junit.xml

test_env.down:
	docker-compose down