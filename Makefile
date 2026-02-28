.PHONY: install lint format test test-live test-all precommit run check prepare serve up down ps

install:
	uv sync

lint:
	uv run ruff check .

format:
	uv run ruff format .

test:
	uv run pytest

test-live:
	uv run pytest -m live -v

test-all:
	uv run pytest -m "" -v

precommit:
	uv run pre-commit run --all-files

run:
	uv run hello

check: lint test

prepare:
	uv run prepare-data $(ARGS)

serve:
	uv run uvicorn airgap_geo_api.app:create_app --factory --reload --port 5000

# ---------------------------------------------------------------------------
# Docker Compose (profiles defined in docker/docker-compose.yml)
#
# Concrete targets:
#   make up       — start all services
#   make down     — stop all services
#   make ps       — list containers
#
# Pattern rules (any profile name works):
#   make <profile>-up    e.g. make nominatim-up, make geocoding-up
#   make <profile>-down  e.g. make routing-down
#   make <profile>-logs  e.g. make nominatim-logs
# ---------------------------------------------------------------------------
COMPOSE = docker compose -f docker/docker-compose.yml --env-file .env

up:
	$(COMPOSE) --profile all up -d

down:
	$(COMPOSE) --profile '*' down

ps:
	$(COMPOSE) ps -a

%-up:
	$(COMPOSE) --profile $* up -d

%-down:
	$(COMPOSE) --profile $* down

%-logs:
	$(COMPOSE) --profile $* logs -f
