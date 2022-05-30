test:
	python -m pytest --cov=./

lint:
	pip install black==22.3.0 isort
	black .
	isort --profile black .

