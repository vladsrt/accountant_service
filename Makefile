test-coverage:
	uv run pytest --cov=app --cov-report=xml:coverage.xml

test:
	uv run pytest

lint:
	uv run ruff format .
	uv run ruff check --fix .

build:
	uv build

install:
	uv sync --all-extras --dev