CODECOV_UPLOAD_TOKEN ?= "notset"
CODECOV_URL ?= "https://api.codecov.io"
CODECOV_FLAG ?= ""
full_sha := $(shell git rev-parse HEAD)
export CODECOV_TOKEN=${CODECOV_UPLOAD_TOKEN}

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
	./tests/reqs.sh

test_env.install_cli:
	pip install codecov-cli

test_env.upload:
	. venv/bin/activate
	codecovcli -u ${CODECOV_URL} do-upload --flag ${CODECOV_FLAG} --fail-on-error

test_env.mutation:
	. venv/bin/activate
	git diff origin/main ${full_sha} > data.patch
	pip install mutmut[patch]
	mutmut run --use-patch-file data.patch || true
	mkdir /tmp/artifacts;
	mutmut junitxml > /tmp/artifacts/mut.xml

test_env.rust_tests:
	curl https://sh.rustup.rs -sSf | sh -s -- -y --default-toolchain nightly
	source $HOME/.cargo/env
	sudo apt-get update
	sudo apt-get install gcc lsb-release wget software-properties-common
	wget https://apt.llvm.org/llvm.sh
	chmod +x llvm.sh
	sudo ./llvm.sh 15
	RUSTFLAGS="-Z instrument-coverage" LLVM_PROFILE_FILE="ribs-%m.profraw" cargo +nightly test --no-default-features
	llvm-profdata-15 merge -sparse ribs-*.profraw -o ribs.profdata
	llvm-cov-15 show --ignore-filename-regex='/.cargo/registry' --instr-profile=ribs.profdata --object `ls target/debug/deps/ribs-* | grep -v "\.d" | grep -v "\.o"` > app.coverage.txt