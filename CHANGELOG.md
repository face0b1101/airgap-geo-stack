# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.2.0] - 2026-02-28

### Added

- **`route_by_name()` convenience function** — geocodes text locations (place names, postcodes, or `"lat,lon"` strings) and routes between them in a single call; returns a `RouteResult` with resolved address metadata
- **`RouteResult` address metadata**: `origin_address`, `destination_address`, and `waypoint_addresses` fields populated when locations are geocoded from text (default to `null`/`[]` for coordinate-only usage)

### Changed

- **Smart `POST /route` endpoint** — `origin`, `destination`, and `waypoints` now accept text strings alongside `{lat, lon}` coordinate objects; all formats can be mixed freely within a single request
- Route cache key computed from **resolved** coordinates so that text and coordinate inputs resolving to the same point share a cache entry

## [1.1.0] - 2026-02-28

### Added

- **Enhanced routing** — `route()` now accepts full OSRM parameter set:
  - `waypoints`: intermediate stops between origin and destination
  - `steps`: request per-leg turn-by-turn manoeuvre steps
  - `alternatives`: request one or more alternative routes
  - `annotations`: per-segment data keys (`duration`, `distance`, `speed`, `nodes`, `weight`, `datasources`)
  - `overview`: geometry detail level (`full`, `simplified`, `false`)
  - `geometries`: encoding format (`polyline`, `polyline6`, `geojson`)
  - `continue_straight`: bias against U-turns at intermediate waypoints
  - `exclude`: road-class avoidance list (e.g. `["motorway"]`, `["toll"]`)
- **New Pydantic models**: `RouteManoeuvre`, `RouteTurnStep`, `RouteLeg` — structured turn-by-turn navigation data
- **`RouteResult` enhancements**: `waypoints` (input intermediates) and `snapped_waypoints` (OSRM-snapped positions) fields; `RouteStep` gains a `legs` list
- **`prepare-data` CLI** (`airgap_geo.cli.prepare_data`) — replaces the old `prepare-data.sh` Bash script with a Python CLI (Typer + Rich) registered as the `prepare-data` entry point
- **Live integration test suite** (`tests/test_live/`) with a `live` pytest marker; skipped by default (`-m 'not live'`)
- **`live` pytest marker** registered in `pyproject.toml`; `addopts` excludes live tests in standard `make test` runs
- **Makefile targets**: `test-live`, `test-all`, `up`, `down`, `ps`, and pattern rules `<profile>-up`, `<profile>-down`, `<profile>-logs`
- **Seven Jupyter notebooks** (`notebooks/01` – `07`) covering geocoding, routing, enhanced routing, postcodes, combined workflow, FastAPI usage, and performance benchmarking, plus a `notebooks/README.md`

### Changed

- **Docker Compose consolidated**: three separate per-service compose files (`nominatim/`, `osrm/`, `photon/`) merged into a single `docker/docker-compose.yml` with named profiles (`geocoding`, `nominatim`, `photon`, `routing`, `osrm`, `postcodes`, `api`, `all`)
- `make prepare` now invokes `uv run prepare-data` instead of the removed `docker/prepare-data.sh`
- `RouteRequest` in the API router now exposes all new routing parameters; cache key derived from a SHA-256 hash of the full request body
- API `POST /route` description updated to reflect multi-waypoint and full-parameter support

### Removed

- `docker/nominatim/docker-compose.yml`, `docker/osrm/docker-compose.yml`, `docker/photon/docker-compose.yml` — superseded by the consolidated compose file
- `docker/prepare-data.sh` — superseded by the `prepare-data` Python CLI
- `notebooks/demo.ipynb` — superseded by the numbered notebook series

## [1.0.0] - 2026-02-28

### Added

- **FastAPI REST API** (`airgap_geo_api`) exposing all services over a single port with normalised JSON responses
  - `GET /geocode` — forward and reverse geocoding
  - `POST /route` — driving / walking / cycling route calculation
  - `GET /postcodes/{postcode}` and `GET /outcodes/{outcode}` — UK postcode lookups
  - `GET /health` — per-service health status and latency
  - `make serve` target and Docker API service (`docker/api/Dockerfile`)
- **Pydantic response models** (`models.py`): `GeoPoint`, `Address`, `GeocodeResult`, `RouteResult`, `RouteStep`, `PostcodeResult`, `OutcodeResult`
- **In-process TTL cache** (`cache.py`) for all read endpoints, configurable via `CACHE_TTL_SECONDS` / `CACHE_MAX_SIZE`
- **API test suite** (`tests/test_api/`) covering all endpoints and health checks
- Configurable PBF region via `PBF_URL` / `PBF_REGION` environment variables — any Geofabrik extract can be used
- ARM64 / Apple Silicon support: `OSRM_IMAGE` / `OSRM_PLATFORM` env vars and `docker/build-osrm-arm64.sh` helper script
- `prepare-data.sh` improvements: `--force` flag, `--threads N` for constrained-RAM machines, idempotent stage skipping

### Changed

- **Renamed package** from `airgap_geocoding` to `airgap_geo`; project name from `airgap-geocoding-stack` to `airgap-geo-stack`
- **Async-first library** — all public functions (`geocoder`, `route`, `lookup_postcode`, `lookup_outcode`) are now `async` and accept an `httpx.AsyncClient`
- Replaced `requests` with `httpx` as the HTTP client
- Replaced `responses` test mocking with `pytest-httpx`; all tests now async via `pytest-asyncio`
- All library functions return structured Pydantic models instead of raw dicts (`None` on failure instead of `{}`)
- Docker Compose: explicit `platform` pinning for amd64-only images; OSRM commands parameterised with `PBF_REGION`
- Dependencies: added `fastapi`, `pydantic`, `uvicorn[standard]`, `cachetools`, `httpx`; removed `requests`

## [0.1.0] - 2026-02-27

### Added

- Initial project created from python-uv-boilerplate template
- `airgap_geocoding` Python library with `geocoder`, `route`, `lookup_postcode`, and `lookup_outcode` public API
- Docker Compose stacks for Nominatim, Photon, OSRM (driving/walking/cycling), HAProxy, and postcodes.io
- Air-gap deployment guide in `docker/README.md`
- pytest test suite using `responses` to mock all HTTP calls

[0.1.0]: https://github.com/face0b1101/airgap-geo-stack/releases/tag/v0.1.0
[1.0.0]: https://github.com/face0b1101/airgap-geo-stack/compare/v0.1.0...v1.0.0
[1.1.0]: https://github.com/face0b1101/airgap-geo-stack/compare/v1.0.0...v1.1.0
[1.2.0]: https://github.com/face0b1101/airgap-geo-stack/compare/v1.1.0...v1.2.0
[unreleased]: https://github.com/face0b1101/airgap-geo-stack/compare/v1.2.0...HEAD
