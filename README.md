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
before the Docker stack will start. A unified preparation script handles everything:

```bash
make prepare                             # download and process all services
make prepare ARGS="--cleanup"            # same, but remove PBF copies from OSRM dirs afterwards
make prepare ARGS="--skip-photon"        # skip the ~60 GB Photon download
```

Individual services can be skipped with `--skip-nominatim`, `--skip-osrm`, or `--skip-photon`.

| Service          | What it needs                                                   | Approx. size               | Time                              |
| ---------------- | --------------------------------------------------------------- | -------------------------- | --------------------------------- |
| **Nominatim**    | PBF download (set `PBF_URL`/`PBF_REGION`); import on first `docker compose up` | ~1.2 GB download           | minutes (download), 2–6 hr import |
| **OSRM**         | PBF download + extract/partition/customise per profile          | ~1.2 GB + ~10 GB processed | 1–3 hours                         |
| **Photon**       | European dataset download                                       | ~60 GB                     | hours (network-dependent)         |
| **postcodes.io** | None — data is pre-loaded in the DB image                       | —                          | —                                 |

See individual service READMEs for details:
[`docker/nominatim/README.md`](docker/nominatim/README.md),
[`docker/osrm/README.md`](docker/osrm/README.md),
[`docker/photon/README.md`](docker/photon/README.md).

______________________________________________________________________

## REST API (FastAPI)

An HTTP API layer wraps the Python library, exposing all four services over a single port with normalised JSON responses. It is suitable for non-Python consumers or multi-language teams.

### Running locally

```bash
make serve          # starts uvicorn on http://localhost:5000 with --reload
```

Interactive docs are available at `http://localhost:5000/docs` (Swagger UI) and `http://localhost:5000/redoc`.

### Running via Docker Compose

The `api` service is included in [`docker/docker-compose.yml`](docker/docker-compose.yml) and depends on all four backends:

```bash
docker compose --env-file .env up -d api
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
  "origin":      { "lat": 51.5034, "lon": -0.1276 },
  "destination": { "lat": 53.4808, "lon": -2.2426 },
  "profile":     "driving"
}
```

`profile` must be one of `"driving"`, `"walking"`, or `"cycling"`.

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

| Variable            | Default                 | Description                                                                      |
| ------------------- | ----------------------- | -------------------------------------------------------------------------------- |
| `PHOTON_API`        | `http://localhost:2322` | Photon reverse geocoding service                                                 |
| `NOMINATIM_URL`     | `http://localhost:8080` | Nominatim geocoding service                                                      |
| `OSRM_API`          | `http://localhost:80`   | OSRM routing API (via HAProxy)                                                   |
| `POSTCODES_URL`     | `http://localhost:8000` | postcodes.io API                                                                 |
| `API_PORT`          | `5000`                  | Port the FastAPI service listens on                                              |
| `CACHE_TTL_SECONDS` | `3600`                  | Cache entry TTL in seconds                                                       |
| `CACHE_MAX_SIZE`    | `1024`                  | Max entries per cache domain                                                     |
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
