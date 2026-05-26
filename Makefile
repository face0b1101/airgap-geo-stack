.PHONY: install lint format test test-live test-all smoke-test precommit run check prepare serve osrm-build up down ps status

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

smoke-test:  ## HTTP smoke checks against running Docker stack (see scripts/smoke-test.sh)
	@./scripts/smoke-test.sh

precommit:
	uv run pre-commit run --all-files

run:
	uv run hello

check: lint test

prepare:
	uv run prepare-data $(ARGS)

serve:
	uv run uvicorn airgap_geo_api.app:create_app --factory --reload --port 5050

osrm-build:  ## Build OSRM from source using OSRM_IMAGE / OSRM_PLATFORM from .env
	docker/build-osrm.sh --platform $(OSRM_PLATFORM) --tag $(OSRM_IMAGE)

# ---------------------------------------------------------------------------
# Docker Compose (profiles defined in docker/docker-compose.yml)
#
# Concrete targets:
#   make up       — start all services
#   make down     — stop all services
#   make ps       — list containers
#   make status   — check readiness of backend services
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

define _STATUS_PY
import httpx, time
from airgap_geo.settings import API_PORT, NOMINATIM_URL, OSRM_API, PHOTON_API, POSTCODES_URL
urls = {
    'api':          f'http://localhost:{API_PORT}/health',
    'nominatim':    NOMINATIM_URL + '/status.php',
    'photon':       PHOTON_API + '/api?q=london&limit=1',
    'osrm':         OSRM_API + '/route/v1/driving/-0.1276,51.5034;-0.1276,51.5034',
    'postcodes_io': POSTCODES_URL + '/postcodes/SW1A2AA',
}
with httpx.Client() as c:
    for name, url in urls.items():
        t0 = time.monotonic()
        try:
            r = c.get(url, timeout=5.0)
            ms = (time.monotonic() - t0) * 1000
            ok = r.is_success
            code = r.status_code
        except Exception:
            ms = (time.monotonic() - t0) * 1000
            ok = False
            code = 'ERR'
        sym = '\033[32m✓\033[0m' if ok else '\033[31m✗\033[0m'
        print(f'  {sym} {name:<14s} {code:<5}  ({ms:.0f} ms)')
endef
export _STATUS_PY

status:  ## Check readiness of all backend services
	@uv run python -c "$$_STATUS_PY"

%-up:
	$(COMPOSE) --profile $* up -d

%-down:
	$(COMPOSE) --profile $* down

%-logs:
	$(COMPOSE) --profile $* logs -f
