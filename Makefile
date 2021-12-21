test:
	python -m pytest --cov=./

lint:
	pip install black==19.10b0 isort
	black .
	isort --profile black .

