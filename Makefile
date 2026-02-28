.PHONY: install lint format test precommit run check prepare serve

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

prepare:
	cd docker && bash prepare-data.sh $(ARGS)

serve:
	uv run uvicorn airgap_geo_api.app:create_app --factory --reload --port 5000
