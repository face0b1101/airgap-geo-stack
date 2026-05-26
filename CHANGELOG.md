# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.5.0] - 2026-05-26

### Added

- **`make status` target** — probes all backend services (API, Nominatim, Photon, OSRM, postcodes.io) and prints a colour-coded readiness table with HTTP status and latency
- **`make smoke-test` target** and **`scripts/smoke-test.sh`** — HTTP smoke checks for all backends plus API geocode, postcode, and route endpoints; optional `--pytest` runs the live test suite
- **Smoke testing documentation** in README — Quick Start verification step, automated checks table, and manual `curl` examples
- **GB postcodes pre-download** — `prepare-data` now downloads `gb_postcodes.csv.gz` from nominatim.org as step 1b, eliminating the runtime SCP fetch that would fail in air-gapped environments
- **`docs/AIRGAP_TRANSFER.md`** — full USB export/import guide for air-gap deployment

### Changed

- **Nominatim PostgreSQL tuning** — `shm_size` increased from `1g` to `4g`; added `POSTGRES_MAINTENANCE_WORK_MEM=2GB` and other overrides to prevent OOM kills during search index creation on machines with ~25 GB RAM
- **`IMPORT_GB_POSTCODES`** changed from `true` (triggers runtime SCP download) to a container-internal file path (`/nominatim/data/gb_postcodes.csv.gz`) so Nominatim symlinks the pre-downloaded file instead
- FastAPI app version aligned with package version (`1.5.0`)

## [1.4.0] - 2026-03-01

### Added

- **Cross-platform Docker builds** — `FORCE_PLATFORM` env var forces all services to a target architecture (e.g. `linux/amd64` for airgap export from ARM64 hosts)
- **`docker/docker-compose.platform.yml`** override file that constrains every service to `${FORCE_PLATFORM}`; auto-included by the Makefile when the variable is set
- **`make osrm-build` target** — builds OSRM v6.0.0 from source, respecting `OSRM_IMAGE` / `OSRM_PLATFORM` from `.env`
- **`docker/build-osrm.sh`** — replaces `build-osrm-arm64.sh`; accepts `--platform` and `--tag` flags for any architecture; detects cross-compilation and disables LTO to avoid QEMU jobserver bug
- **`prepare-data --verbose`** (`-v`) flag streams full Docker output instead of a spinner
- **OOM auto-retry** for `osrm-extract` — detects exit 137 and retries with halved thread count; prints Docker Desktop / Colima memory advice if it fails at 1 thread
- **Photon progress monitoring** — real-time progress bar tracking directory size, resume detection for partial downloads, and milestone parsing from container stdout
- Per-step elapsed time display and `failed` status in the preparation summary table

### Changed

- **OSRM image fully configurable via `.env`** — `OSRM_IMAGE` and `OSRM_PLATFORM` are the single source of truth for all OSRM operations (data preparation, runtime, image building)
- Makefile loads `.env` and exports key variables; `COMPOSE` definition conditionally includes `docker-compose.platform.yml` when `FORCE_PLATFORM` is set
- Docker Compose: Photon switched from named volume to bind mount (`./photon-data`); postcodes-api `POSTGRES_DATABASE` corrected to `postcodesio`; postcodes-api ports exposed directly (`8000:8000`); Photon container gets `PUID`/`PGID` env vars
- OSRM extract idempotency now checks `.osrm.ebg` (produced last) instead of `.osrm` (produced early) so partially-killed extracts are properly re-run
- `prepare-data` error handling: failing steps no longer abort the entire run — remaining steps continue and the summary shows failed items with a non-zero exit code
- README: Quick Start walkthrough (1–5), cross-platform builds section, new env vars (`OSRM_IMAGE`, `OSRM_PLATFORM`, `OSRM_DATA`, `FORCE_PLATFORM`) in config table
- Air-gap image export uses `OSRM_IMAGE` from `.env` and respects `FORCE_PLATFORM` for `docker pull`
- Updated `docker/README.md` and `docker/osrm/README.md` for the new build workflow
- Notebooks re-executed with latest outputs

### Removed

- `docker/build-osrm-arm64.sh` — superseded by `docker/build-osrm.sh`
- `photon-data` named Docker volume — replaced by a bind mount

## [1.3.0] - 2026-02-28

### Added

- **`resolve_addresses` opt-in flag** on `POST /route` — when `true`, coordinate (`{lat, lon}`) inputs are reverse-geocoded via Photon to populate `origin_address`, `destination_address`, and `waypoint_addresses` (default `false` preserves existing performance)
- `resolve_addresses` keyword argument on `route_by_name()` for API parity (no-op since text inputs are always geocoded)

### Changed

- `_resolve_location` helper reverse-geocodes `GeoPoint` inputs when the flag is set
- Route cache key now includes `resolve_addresses` so `true`/`false` requests produce separate cache entries

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
- ARM64 / Apple Silicon support: `OSRM_IMAGE` / `OSRM_PLATFORM` env vars and `docker/build-osrm.sh` helper script
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
[1.3.0]: https://github.com/face0b1101/airgap-geo-stack/compare/v1.2.0...v1.3.0
[1.4.0]: https://github.com/face0b1101/airgap-geo-stack/compare/v1.3.0...v1.4.0
[1.5.0]: https://github.com/face0b1101/airgap-geo-stack/compare/v1.4.0...v1.5.0
[unreleased]: https://github.com/face0b1101/airgap-geo-stack/compare/v1.5.0...HEAD
