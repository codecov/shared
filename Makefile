CODECOV_UPLOAD_TOKEN ?= "notset"
CODECOV_URL ?= "https://api.codecov.io"
CODECOV_FLAG ?= ""
full_sha := $(shell git rev-parse HEAD)
export CODECOV_TOKEN=${CODECOV_UPLOAD_TOKEN}
.ONESHELL:

test:
	# Emit coverage/junit files inside the bind-mounted `test` directory
	docker compose exec shared uv run pytest --cov-report=xml:tests/unit.coverage.xml --junitxml=tests/unit.junit.xml -o junit_family=legacy

test.path:
	docker compose exec shared uv run pytest $(TEST_PATH)

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
	uv sync
	. .venv/bin/activate

test_env.install_cli:
	pip install codecov-cli

test_env.build:
	docker compose build

test_env.up:
	docker compose up -d

test_env.test:
	# Emit coverage/junit files inside the bind-mounted `test` directory
	docker compose exec shared uv run pytest --cov ./shared --cov-report=xml:tests/unit.coverage.xml --junitxml=tests/unit.junit.xml -o junit_family=legacy

test_env.down:
	docker compose down
