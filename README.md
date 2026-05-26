# `airgap-geo-stack`

A self-contained Python library and Docker Compose stack for fully air-gapped geocoding,
reverse geocoding, routing, and UK postcode lookup - with zero runtime dependency on
external APIs or the internet.

All services are OSM-derived and run entirely within your own infrastructure.

______________________________________________________________________

## Quick Start

1. **Clone and install**

```bash
git clone https://github.com/face0b1101/airgap-geo-stack
cd airgap-geo-stack
make install
```

2. **Configure**

```bash
cp .env.example .env
# Edit .env — set PBF_REGION / PBF_URL for your area
```

3. **Build OSRM from source** *(optional — only needed for ARM64 or v6.0.0)*

```bash
# Set OSRM_IMAGE and OSRM_PLATFORM in .env, then:
make osrm-build
```

4. **Prepare data**

```bash
make prepare                          # all services
make prepare ARGS="--skip-photon"     # skip the ~60 GB Photon download
```

5. **Start services**

```bash
make up
```

6. **Verify the stack**

```bash
make status              # quick per-service readiness (HTTP probes)
make smoke-test          # smoke-test backends + API endpoints
make test-live           # full pytest integration suite (optional)
```

See [Smoke testing](#smoke-testing) for manual `curl` examples.

______________________________________________________________________

## Services

| Service              | Image                                   | Port     | Role                                                      |
| -------------------- | --------------------------------------- | -------- | --------------------------------------------------------- |
| **Nominatim**        | `mediagis/nominatim:5.2`                | `8080`   | Forward geocoding - place name / postcode → lat/lon       |
| **Photon**           | `rtuszik/photon-docker:latest`          | `2322`   | Reverse geocoding - lat/lon → rich OSM address properties |
| **OSRM** (driving)   | `${OSRM_IMAGE}`                         | internal | Road routing, car profile                                 |
| **OSRM** (walking)   | `${OSRM_IMAGE}`                         | internal | Road routing, foot profile                                |
| **OSRM** (cycling)   | `${OSRM_IMAGE}`                         | internal | Road routing, bike profile                                |
| **OSRM frontend**    | `osrm/osrm-frontend:latest`             | `9966`   | Visual route planner UI                                   |
| **HAProxy**          | `haproxy`                               | `80`     | Reverse proxy for OSRM profiles and postcodes.io          |
| **postcodes.io API** | `idealpostcodes/postcodes.io:latest`    | `8000`   | UK postcode lookup                                        |
| **postcodes.io DB**  | `idealpostcodes/postcodes.io.db:latest` | internal | PostgreSQL backing store                                  |
| **Airgap API**       | *(built locally)*                       | `5050`   | Unified FastAPI service exposing all four services        |

See [`docker/README.md`](docker/README.md) for deployment details and
[`docs/AIRGAP_TRANSFER.md`](docs/AIRGAP_TRANSFER.md) for the full air-gap
USB export/import guide.

______________________________________________________________________

## Data Preparation (required before first run)

All services except postcodes.io require data to be downloaded and/or processed
before the Docker stack will start. A Python CLI (powered by Typer + Rich) handles
everything with progress bars and clear status output:

```bash
make prepare                             # download and process all services
make prepare ARGS="--cleanup"            # same, but remove PBF copies from OSRM dirs afterwards
make prepare ARGS="--skip-photon"        # skip the ~60 GB Photon download
uv run prepare-data --help               # see all available options
```

Individual services can be skipped with `--skip-nominatim`, `--skip-osrm`, or `--skip-photon`.

| Service          | What it needs                                                                  | Approx. size               | Time                              |
| ---------------- | ------------------------------------------------------------------------------ | -------------------------- | --------------------------------- |
| **Nominatim**    | PBF download (set `PBF_URL`/`PBF_REGION`); import on first `docker compose up` | ~1.2 GB download           | minutes (download), 2–6 hr import |
| **OSRM**         | PBF download + extract/partition/customise per profile                         | ~1.2 GB + ~10 GB processed | 1–3 hours                         |
| **Photon**       | European dataset download                                                      | ~60 GB                     | hours (network-dependent)         |
| **postcodes.io** | None — data is pre-loaded in the DB image                                      | —                          | —                                 |

See individual service READMEs for details:
[`docker/nominatim/README.md`](docker/nominatim/README.md),
[`docker/osrm/README.md`](docker/osrm/README.md),
[`docker/photon/README.md`](docker/photon/README.md).

______________________________________________________________________

## Docker Services

All services are defined in a single [`docker/docker-compose.yml`](docker/docker-compose.yml)
and controlled via **profiles** so you can start only what you need.

### Profiles

| Profile     | Services included                                                 |
| ----------- | ----------------------------------------------------------------- |
| `nominatim` | Nominatim                                                         |
| `photon`    | Photon                                                            |
| `geocoding` | Nominatim + Photon                                                |
| `osrm`      | OSRM backends (driving/walking/cycling) + HAProxy + OSRM frontend |
| `postcodes` | postcodes.io API + DB                                             |
| `routing`   | OSRM + HAProxy + OSRM frontend + postcodes.io                     |
| `api`       | FastAPI service                                                   |
| `all`       | Everything                                                        |

### Make targets

```bash
make up                  # start all services
make down                # stop all services
make ps                  # list running containers

make nominatim-up        # start Nominatim only
make geocoding-up        # start Nominatim + Photon
make routing-up          # start OSRM + postcodes.io
make api-up              # start the FastAPI service

make osrm-build          # build OSRM from source (uses OSRM_IMAGE / OSRM_PLATFORM from .env)

make nominatim-logs      # tail Nominatim logs
make routing-down        # stop routing services
```

Any profile name works with `-up`, `-down`, and `-logs` suffixes.

### Cross-platform builds (airgap export)

To prepare images and data on one architecture (e.g. arm64) for
deployment on another (e.g. x86_64), set `FORCE_PLATFORM` in `.env`:

```bash
# .env
FORCE_PLATFORM=linux/amd64
OSRM_IMAGE=osrm-backend:amd64-local
OSRM_PLATFORM=linux/amd64
```

Then build and prepare:

```bash
make osrm-build          # builds OSRM v6 for linux/amd64
make prepare             # processes data using the amd64 image
make up                  # runs all services forced to linux/amd64
make status              # checks that all services are running and ready
```

The upstream `osrm/osrm-backend` image on Docker Hub is v5.26.0 (amd64-only).
If you build from source you get v6.0.0 — the data formats are incompatible,
so the same image version must be used for both data preparation and runtime.
`make osrm-build` ensures the built image tag matches `OSRM_IMAGE` in `.env`.

See [`docker/README.md`](docker/README.md) for deployment and configuration, and
[`docs/AIRGAP_TRANSFER.md`](docs/AIRGAP_TRANSFER.md) for the complete USB
export/import guide (bash, zsh, and fish commands included).

______________________________________________________________________

## Smoke testing

After `make up`, confirm every backend is reachable and the unified API returns
sensible results.

### Automated checks

| Command | What it does |
| ------- | ------------ |
| `make status` | One-line HTTP probe per backend (Nominatim, Photon, OSRM, postcodes.io, API `/health`) |
| `make smoke-test` | Same backends plus API geocode, postcode, and short route checks |
| `./scripts/smoke-test.sh --pytest` | Smoke checks, then `make test-live` (full integration tests) |
| `make test-live` | Pytest suite against live services (`tests/test_live/`) |

`make smoke-test` exits non-zero if any probe fails. Install `jq` for stricter
JSON assertions on `/health` and `/geocode` (without `jq`, HTTP status codes only).

### Manual `curl` examples

Backend services (defaults from `.env.example`):

```bash
# Nominatim — import may still be running on first start
curl -sS "${NOMINATIM_URL:-http://localhost:8080}/status.php" | head

# Photon — reverse geocode probe
curl -sS "${PHOTON_API:-http://localhost:2322}/api?q=london&limit=1" | head

# OSRM via HAProxy — zero-length route (health-style probe)
curl -sS "${OSRM_API:-http://localhost:80}/route/v1/driving/-0.1276,51.5034;-0.1276,51.5034"

# postcodes.io
curl -sS "${POSTCODES_URL:-http://localhost:8000}/postcodes/SW1A2AA"
```

Airgap API (`API_PORT` defaults to `5050`):

```bash
API=http://localhost:${API_PORT:-5050}

curl -sS "$API/health" | jq .
curl -sS "$API/geocode?q=51.5034,-0.1276" | jq .
curl -sS "$API/postcodes/SW1A2AA" | jq .
curl -sS -X POST "$API/route" \
  -H 'Content-Type: application/json' \
  -d '{"origin":{"lat":51.5034,"lon":-0.1276},"destination":{"lat":51.5074,"lon":-0.1278},"profile":"driving"}' \
  | jq '.routes[0].distance_m'
```

Interactive API docs: `http://localhost:5050/docs`.

______________________________________________________________________

## REST API (FastAPI)

An HTTP API layer wraps the Python library, exposing all four services over a single port with normalised JSON responses. It is suitable for non-Python consumers or multi-language teams.

### Running locally

```bash
make serve          # starts uvicorn on http://localhost:5050 with --reload
```

Interactive docs are available at `http://localhost:5050/docs` (Swagger UI) and `http://localhost:5050/redoc`.

### Running via Docker Compose

The `api` service is included in [`docker/docker-compose.yml`](docker/docker-compose.yml):

```bash
make api-up              # just the API service
make up                  # all services (API + all backends)
```

### Endpoints

| Method | Path                    | Description                                                                    |
| ------ | ----------------------- | ------------------------------------------------------------------------------ |
| GET    | `/geocode?q={query}`    | Forward geocode a place name / postcode, or reverse geocode a `lat,lon` string |
| POST   | `/route`                | Calculate a driving / walking / cycling route                                  |
| GET    | `/postcodes/{postcode}` | UK full postcode lookup                                                        |
| GET    | `/outcodes/{outcode}`   | UK outcode (district) lookup                                                   |
| GET    | `/health`               | Per-service health status and latency                                          |

#### POST /route — request body

`origin`, `destination`, and each item in `waypoints` accept **either** a
`{lat, lon}` coordinate object **or** a text string (place name, postcode, or
`"lat,lon"`). Text values are geocoded automatically via Nominatim before
routing. All formats can be mixed freely within a single request.

```json
{
  "origin":           "Westminster",
  "destination":      "Birmingham",
  "profile":          "driving",
  "waypoints":        ["Oxford"],
  "steps":            false,
  "alternatives":     false,
  "annotations":      null,
  "overview":         "full",
  "geometries":       "polyline",
  "continue_straight": null,
  "exclude":          null
}
```

Coordinate objects still work as before:

```json
{
  "origin":      { "lat": 51.5034, "lon": -0.1276 },
  "destination": { "lat": 53.4808, "lon": -2.2426 }
}
```

Mixed input (coordinate origin, text destination) is also supported:

```json
{
  "origin":      { "lat": 51.5034, "lon": -0.1276 },
  "destination": "Birmingham"
}
```

#### Example — route by name with `curl`

```bash
curl -s -X POST http://localhost:5050/route \
  -H 'Content-Type: application/json' \
  -d '{"origin": "Westminster", "destination": "Birmingham", "profile": "driving"}'
```

The response includes the resolved coordinates **and** address metadata for
any text-based inputs:

```json
{
  "profile": "driving",
  "origin":              { "lat": 51.4975, "lon": -0.1357 },
  "destination":         { "lat": 52.4862, "lon": -1.8904 },
  "origin_address":      { "name": "Westminster", "city": "London", "country": "United Kingdom", ... },
  "destination_address": { "name": "Birmingham", "city": "Birmingham", "country": "United Kingdom", ... },
  "waypoint_addresses":  [],
  "routes": [ { "distance_m": 195210.4, "duration_s": 7842.1, "geometry": "...", "legs": [...] } ],
  ...
}
```

#### Example — mixed input with `curl`

Coordinate origin with a text destination and a text waypoint:

```bash
curl -s -X POST http://localhost:5050/route \
  -H 'Content-Type: application/json' \
  -d '{
    "origin":      { "lat": 51.5034, "lon": -0.1276 },
    "destination": "Birmingham",
    "waypoints":   ["Oxford"],
    "profile":     "driving"
  }'
```

Only geocoded locations have their address resolved — coordinate inputs
return `null`:

```json
{
  "profile": "driving",
  "origin":              { "lat": 51.5034, "lon": -0.1276 },
  "destination":         { "lat": 52.4862, "lon": -1.8904 },
  "origin_address":      null,
  "destination_address": { "name": "Birmingham", "city": "Birmingham", "country": "United Kingdom", ... },
  "waypoint_addresses":  [ { "name": "Oxford", "city": "Oxford", "country": "United Kingdom", ... } ],
  "routes": [ { "distance_m": 210530.2, "duration_s": 8415.7, "geometry": "...", "legs": [...] } ],
  ...
}
```

To also reverse-geocode the coordinate origin, set `resolve_addresses`:

```bash
curl -s -X POST http://localhost:5050/route \
  -H 'Content-Type: application/json' \
  -d '{
    "origin":             { "lat": 51.5034, "lon": -0.1276 },
    "destination":        "Birmingham",
    "waypoints":          ["Oxford"],
    "profile":            "driving",
    "resolve_addresses":  true
  }'
```

Now all address fields are populated:

```json
{
  "profile": "driving",
  "origin":              { "lat": 51.5034, "lon": -0.1276 },
  "destination":         { "lat": 52.4862, "lon": -1.8904 },
  "origin_address":      { "name": "Westminster", "city": "London", "country": "United Kingdom", ... },
  "destination_address": { "name": "Birmingham", "city": "Birmingham", "country": "United Kingdom", ... },
  "waypoint_addresses":  [ { "name": "Oxford", "city": "Oxford", "country": "United Kingdom", ... } ],
  "routes": [ { "distance_m": 210530.2, "duration_s": 8415.7, "geometry": "...", "legs": [...] } ],
  ...
}
```

All fields except `origin` and `destination` are optional.

| Field               | Type                                                                  | Default      | Description                                             |
| ------------------- | --------------------------------------------------------------------- | ------------ | ------------------------------------------------------- |
| `origin`            | `{lat, lon}` \| `string`                                              | *(required)* | Start location — coordinates or text                    |
| `destination`       | `{lat, lon}` \| `string`                                              | *(required)* | End location — coordinates or text                      |
| `profile`           | `"driving"` \| `"walking"` \| `"cycling"`                             | `"driving"`  | Routing profile                                         |
| `waypoints`         | `[{lat, lon} \| string, ...]`                                         | `null`       | Ordered intermediate points (coordinates or text)       |
| `steps`             | `bool`                                                                | `false`      | Include turn-by-turn manoeuvre steps per leg            |
| `alternatives`      | `bool \| int`                                                         | `false`      | Request alternative routes (`true` for any, or a count) |
| `annotations`       | `["duration"\|"distance"\|"speed"\|"nodes"\|"weight"\|"datasources"]` | `null`       | Per-segment annotation keys                             |
| `overview`          | `"full"` \| `"simplified"` \| `"false"`                               | `"full"`     | Route geometry detail level                             |
| `geometries`        | `"polyline"` \| `"polyline6"` \| `"geojson"`                          | `"polyline"` | Route geometry encoding                                 |
| `continue_straight` | `bool`                                                                | `null`       | Bias against U-turns at waypoints                       |
| `exclude`           | `["motorway"\|"toll"\|"ferry", ...]`                                  | `null`       | Road classes to avoid                                   |
| `resolve_addresses` | `bool`                                                                | `false`      | Reverse-geocode coordinate inputs to populate addresses |

Text inputs are always geocoded and their addresses are included
automatically. Set `resolve_addresses: true` to also reverse-geocode
coordinate (`{lat, lon}`) inputs via Photon — useful when you need address
metadata for every point regardless of input format.

| Response field        | Type              | Description                                                          |
| --------------------- | ----------------- | -------------------------------------------------------------------- |
| `origin_address`      | `Address \| null` | Resolved address for origin (populated for text or when flag is set) |
| `destination_address` | `Address \| null` | Resolved address for destination                                     |
| `waypoint_addresses`  | `[Address, ...]`  | Resolved addresses for geocoded waypoints                            |

### Caching

All read endpoints use an in-process TTL cache (default: 1 hour, max 1024 entries per domain). Configure via environment variables:

| Variable            | Default | Description                      |
| ------------------- | ------- | -------------------------------- |
| `CACHE_TTL_SECONDS` | `3600`  | Time-to-live for cached results  |
| `CACHE_MAX_SIZE`    | `1024`  | Maximum entries per cache domain |

______________________________________________________________________

## Python Library

### Installation

```bash
git clone https://github.com/face0b1101/airgap-geo-stack
cd airgap-geo-stack
make install   # runs uv sync - installs all dependencies
```

### Quick start

All public functions are `async` and require an `httpx.AsyncClient`:

```python
import asyncio
import httpx
from airgap_geo import geocoder, route, route_by_name, lookup_postcode, lookup_outcode

async def main():
    async with httpx.AsyncClient() as client:
        # Forward geocode a place name or postcode
        result = await geocoder("10 Downing Street, London", client)

        # Reverse geocode / enrich a coordinate string
        result = await geocoder("51.5034,-0.1276", client)

        # Route by place name (geocodes automatically, includes address metadata)
        r = await route_by_name(
            "Westminster",
            "Birmingham",
            client,
            profile="driving",
            waypoints=["Oxford"],
        )

        # Route between explicit coordinates
        r = await route(
            (51.5034, -0.1276),
            (53.4808, -2.2426),
            client,
            profile="driving",
            waypoints=[(52.4862, -1.8904)],
            steps=True,
        )

        # UK postcode lookup
        info = await lookup_postcode("SW1A 2AA", client)
        outcode = await lookup_outcode("SW1A", client)

asyncio.run(main())
```

### Configuration

All service URLs are read from environment variables (via `python-decouple`). Copy
`.env.example` to `.env` and adjust values to match your deployment:

```bash
cp .env.example .env
```

| Variable            | Default                 | Description                                                                     |
| ------------------- | ----------------------- | ------------------------------------------------------------------------------- |
| `PHOTON_API`        | `http://localhost:2322` | Photon reverse geocoding service                                                |
| `NOMINATIM_URL`     | `http://localhost:8080` | Nominatim geocoding service                                                     |
| `OSRM_API`          | `http://localhost:80`   | OSRM routing API (via HAProxy)                                                  |
| `POSTCODES_URL`     | `http://localhost:8000` | postcodes.io API                                                                |
| `API_PORT`          | `5050`                  | Port the FastAPI service listens on                                             |
| `CACHE_TTL_SECONDS` | `3600`                  | Cache entry TTL in seconds                                                      |
| `CACHE_MAX_SIZE`    | `1024`                  | Max entries per cache domain                                                    |
| `PBF_URL`           | *(Great Britain URL)*   | Full Geofabrik download URL — see [geofabrik.de](https://download.geofabrik.de) |
| `PBF_REGION`        | `great-britain`         | Region stem used in PBF/OSRM filenames (e.g. `germany`, `france`)               |
| `OSRM_IMAGE`        | `osrm/osrm-backend`     | OSRM Docker image — set to a locally built tag for v6.0.0                       |
| `OSRM_PLATFORM`     | `linux/amd64`           | Platform for OSRM containers during data preparation                            |
| `OSRM_DATA`         | `./osrm/data`           | OSRM processed data directory (relative to `docker/`)                           |
| `FORCE_PLATFORM`    | *(unset)*               | Force all Docker images to a specific platform (e.g. `linux/amd64` for export)  |

______________________________________________________________________

## Project Structure

```sh
src/
  airgap_geo/
    __init__.py           # Public API: geocoder, route, lookup_postcode, lookup_outcode + models
    settings.py           # Environment-variable configuration
    models.py             # Pydantic response models (GeoPoint, GeocodeResult, RouteResult, ...)
    geocoding.py          # photon_reverse_geocode, nominatim_geocoder, geocoder
    routing.py            # route
    postcodes.py          # lookup_postcode, lookup_outcode
    cli/
      prepare_data.py     # `uv run prepare-data` — download and process geodata
  airgap_geo_api/
    app.py                # FastAPI app factory and /health endpoint
    cache.py              # In-process TTL cache
    routers/
      geocode.py          # GET /geocode
      routing.py          # POST /route
      postcodes.py        # GET /postcodes/{postcode}, GET /outcodes/{outcode}
docker/
  README.md               # Air-gap deployment guide
  api/Dockerfile          # FastAPI service image
  nominatim/
  photon/
  osrm/
notebooks/
  README.md               # Notebook overview and usage
  01-geocoding.ipynb      # Forward and reverse geocoding
  02-routing.ipynb        # Basic routing
  03-routing-enhanced.ipynb  # Waypoints, steps, alternatives, annotations, exclusions
  04-postcodes.ipynb      # UK postcode and outcode lookups
  05-combined-workflow.ipynb # End-to-end geocode → route → postcode
  06-fastapi.ipynb        # FastAPI REST API usage
  07-performance.ipynb    # Benchmarking and concurrency
tests/
  test_geocoding.py
  test_routing.py
  test_postcodes.py
  test_api/
    test_geocode.py
    test_routing.py
    test_postcodes.py
    test_health.py
  test_live/              # Integration tests (require running Docker services)
    test_integration.py
```

______________________________________________________________________

## Development

### Prerequisites

- [uv](https://docs.astral.sh/uv/) (Python package manager)

### Setup

```bash
make install      # uv sync - install all dependencies
make test         # run the pytest suite (excludes live tests)
make test-live    # run live integration tests (requires running Docker services)
make test-all     # run all tests including live
make smoke-test   # HTTP smoke checks (requires running Docker services)
make status       # per-service readiness probes
make lint       # ruff check
make format     # ruff format
make check      # lint + test combined
```

### Pre-commit hooks (optional)

```bash
uv run pre-commit install
```

______________________________________________________________________

## How to Code

Use conventional commit prefixes:

| Prefix      | Purpose               |
| ----------- | --------------------- |
| `feat:`     | New feature           |
| `fix:`      | Bug fix               |
| `style:`    | Formatting/style only |
| `refactor:` | Refactoring           |
| `test:`     | Tests only            |
| `docs:`     | Documentation only    |
| `chore:`    | Build/tooling         |
| `ci:`       | CI/CD changes         |
