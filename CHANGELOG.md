# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

[Unreleased]: https://github.com/face0b1101/airgap-geo-stack/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/face0b1101/airgap-geo-stack/compare/v0.1.0...v1.0.0
[0.1.0]: https://github.com/face0b1101/airgap-geo-stack/releases/tag/v0.1.0
