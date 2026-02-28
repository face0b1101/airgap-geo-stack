# `airgap-geocoding-stack`

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
| **Nominatim**    | Great Britain PBF download; import on first `docker compose up` | ~1.2 GB download           | minutes (download), 2–6 hr import |
| **OSRM**         | PBF download + extract/partition/customise per profile          | ~1.2 GB + ~10 GB processed | 1–3 hours                         |
| **Photon**       | European dataset download                                       | ~60 GB                     | hours (network-dependent)         |
| **postcodes.io** | None — data is pre-loaded in the DB image                       | —                          | —                                 |

See individual service READMEs for details:
[`docker/nominatim/README.md`](docker/nominatim/README.md),
[`docker/osrm/README.md`](docker/osrm/README.md),
[`docker/photon/README.md`](docker/photon/README.md).

______________________________________________________________________

## Python Library

### Installation

```bash
git clone https://github.com/face0b1101/airgap-geocoding-stack
cd airgap-geocoding-stack
make install   # runs uv sync - installs all dependencies
```

### Quick start

```python
from airgap_geocoding import geocoder, route, lookup_postcode, lookup_outcode

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

| Variable        | Default                 | Description                      |
| --------------- | ----------------------- | -------------------------------- |
| `PHOTON_API`    | `http://localhost:2322` | Photon reverse geocoding service |
| `NOMINATIM_URL` | `http://localhost:8080` | Nominatim geocoding service      |
| `OSRM_API`      | `http://localhost:80`   | OSRM routing API (via HAProxy)   |
| `POSTCODES_URL` | `http://localhost:8000` | postcodes.io API                 |

______________________________________________________________________

## Project Structure

```sh
src/
  airgap_geocoding/
    __init__.py       # Public API: geocoder, route, lookup_postcode, lookup_outcode
    settings.py       # Environment-variable configuration
    geocoding.py      # photon_reverse_geocode, nominatim_geocoder, geocoder
    routing.py        # route
    postcodes.py      # lookup_postcode, lookup_outcode
docker/
  README.md           # Air-gap deployment guide
  nominatim/
  photon/
  osrm/
tests/
  test_geocoding.py
  test_routing.py
  test_postcodes.py
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
