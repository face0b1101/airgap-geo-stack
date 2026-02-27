.PHONY: install lint format test precommit run check

install:
	uv sync

lint:
	uv run ruff check .

format:
	uv run ruff format .

test:
	uv run pytest

precommit:
	uv run pre-commit run --all-files

run:
	uv run hello

check: lint test

