.PHONY: install lint format test test-live test-all precommit run check prepare serve osrm-build up down ps

# Load .env so that FORCE_PLATFORM, OSRM_IMAGE, etc. are available to all
# targets (including `make prepare` which shells out to uv/python).
-include .env
export FORCE_PLATFORM OSRM_IMAGE OSRM_PLATFORM PBF_REGION PBF_URL

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

osrm-build:  ## Build OSRM from source using OSRM_IMAGE / OSRM_PLATFORM from .env
	docker/build-osrm.sh --platform $(OSRM_PLATFORM) --tag $(OSRM_IMAGE)

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
DOCKER := $(or $(shell command -v docker 2>/dev/null),$(wildcard /opt/homebrew/bin/docker),$(wildcard /usr/local/bin/docker))
ifdef FORCE_PLATFORM
COMPOSE = $(DOCKER) compose -f docker/docker-compose.yml -f docker/docker-compose.platform.yml --env-file .env
else
COMPOSE = $(DOCKER) compose -f docker/docker-compose.yml --env-file .env
endif

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
