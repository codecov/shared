test:
	python -m pytest --cov=./

lint:
	pip install black==19.10b0 isort
	black --check .
	isort --profile black .

