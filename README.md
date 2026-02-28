# `airgap-geo-stack`

A self-contained Python library and Docker Compose stack for fully air-gapped geocoding,
reverse geocoding, routing, and UK postcode lookup - with zero runtime dependency on
external APIs or the internet.

All services are OSM-derived and run entirely within your own infrastructure.

______________________________________________________________________

## Services

| Service              | Image                                   | Port     | Role                                                      |
| -------------------- | --------------------------------------- | -------- | --------------------------------------------------------- |
| **Nominatim**        | `mediagis/nominatim:5.2`                | `8080`   | Forward geocoding - place name / postcode → lat/lon       |
| **Photon**           | `rtuszik/photon-docker:latest`          | `2322`   | Reverse geocoding - lat/lon → rich OSM address properties |
| **OSRM** (driving)   | `osrm/osrm-backend`                     | internal | Road routing, car profile                                 |
| **OSRM** (walking)   | `osrm/osrm-backend`                     | internal | Road routing, foot profile                                |
| **OSRM** (cycling)   | `osrm/osrm-backend`                     | internal | Road routing, bike profile                                |
| **OSRM frontend**    | `osrm/osrm-frontend:latest`             | `9966`   | Visual route planner UI                                   |
| **HAProxy**          | `haproxy`                               | `80`     | Reverse proxy for OSRM profiles and postcodes.io          |
| **postcodes.io API** | `idealpostcodes/postcodes.io:latest`    | `8000`   | UK postcode lookup                                        |
| **postcodes.io DB**  | `idealpostcodes/postcodes.io.db:latest` | internal | PostgreSQL backing store                                  |

See [`docker/README.md`](docker/README.md) for full deployment and air-gap transfer instructions.

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

make nominatim-logs      # tail Nominatim logs
make routing-down        # stop routing services
```

Any profile name works with `-up`, `-down`, and `-logs` suffixes.

See [`docker/README.md`](docker/README.md) for full deployment, configuration, and air-gap transfer instructions.

______________________________________________________________________

## REST API (FastAPI)

An HTTP API layer wraps the Python library, exposing all four services over a single port with normalised JSON responses. It is suitable for non-Python consumers or multi-language teams.

### Running locally

```bash
make serve          # starts uvicorn on http://localhost:5000 with --reload
```

Interactive docs are available at `http://localhost:5000/docs` (Swagger UI) and `http://localhost:5000/redoc`.

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

```json
{
  "origin":           { "lat": 51.5034, "lon": -0.1276 },
  "destination":      { "lat": 53.4808, "lon": -2.2426 },
  "profile":          "driving",
  "waypoints":        [{ "lat": 52.4862, "lon": -1.8904 }],
  "steps":            false,
  "alternatives":     false,
  "annotations":      null,
  "overview":         "full",
  "geometries":       "polyline",
  "continue_straight": null,
  "exclude":          null
}
```

All fields except `origin` and `destination` are optional.

| Field               | Type                                                                  | Default      | Description                                             |
| ------------------- | --------------------------------------------------------------------- | ------------ | ------------------------------------------------------- |
| `profile`           | `"driving"` \| `"walking"` \| `"cycling"`                             | `"driving"`  | Routing profile                                         |
| `waypoints`         | `[{lat, lon}, ...]`                                                   | `null`       | Ordered intermediate points                             |
| `steps`             | `bool`                                                                | `false`      | Include turn-by-turn manoeuvre steps per leg            |
| `alternatives`      | `bool \| int`                                                         | `false`      | Request alternative routes (`true` for any, or a count) |
| `annotations`       | `["duration"\|"distance"\|"speed"\|"nodes"\|"weight"\|"datasources"]` | `null`       | Per-segment annotation keys                             |
| `overview`          | `"full"` \| `"simplified"` \| `"false"`                               | `"full"`     | Route geometry detail level                             |
| `geometries`        | `"polyline"` \| `"polyline6"` \| `"geojson"`                          | `"polyline"` | Route geometry encoding                                 |
| `continue_straight` | `bool`                                                                | `null`       | Bias against U-turns at waypoints                       |
| `exclude`           | `["motorway"\|"toll"\|"ferry", ...]`                                  | `null`       | Road classes to avoid                                   |

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

```python
from airgap_geo import geocoder, route, lookup_postcode, lookup_outcode

# Forward geocode a place name or postcode
result = geocoder("10 Downing Street, London")

# Reverse geocode / enrich a coordinate string
result = geocoder("51.5034,-0.1276")

# Driving route between two points
r = route((51.5034, -0.1276), (53.4808, -2.2426), profile="driving")

# UK postcode lookup
info = lookup_postcode("SW1A 2AA")
outcode = lookup_outcode("SW1A")
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
| `API_PORT`          | `5000`                  | Port the FastAPI service listens on                                             |
| `CACHE_TTL_SECONDS` | `3600`                  | Cache entry TTL in seconds                                                      |
| `CACHE_MAX_SIZE`    | `1024`                  | Max entries per cache domain                                                    |
| `PBF_URL`           | *(Great Britain URL)*   | Full Geofabrik download URL — see [geofabrik.de](https://download.geofabrik.de) |
| `PBF_REGION`        | `great-britain`         | Region stem used in PBF/OSRM filenames (e.g. `germany`, `france`)               |

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
tests/
  test_geocoding.py
  test_routing.py
  test_postcodes.py
  test_api/
    test_geocode.py
    test_routing.py
    test_postcodes.py
    test_health.py
```

______________________________________________________________________

## Development

### Prerequisites

- [uv](https://docs.astral.sh/uv/) (Python package manager)

### Setup

```bash
make install    # uv sync - install all dependencies
make test       # run the pytest suite
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
