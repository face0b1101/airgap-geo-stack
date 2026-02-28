# Air-Gap Geocoding Stack - Docker Deployment Guide

A single `docker-compose.yml` manages all services. Docker Compose **profiles**
let you start only what you need.

______________________________________________________________________

## Services

| Service              | Profile(s)           | Port     | Purpose                                                    |
| -------------------- | -------------------- | -------- | ---------------------------------------------------------- |
| **Nominatim**        | geocoding, nominatim | `8080`   | Forward geocoding - place/postcode → lat/lon               |
| **Photon**           | geocoding, photon    | `2322`   | Reverse geocoding - lat/lon → OSM address                  |
| **OSRM driving**     | routing, osrm        | internal | Car route calculation                                      |
| **OSRM walking**     | routing, osrm        | internal | Foot route calculation                                     |
| **OSRM cycling**     | routing, osrm        | internal | Bike route calculation                                     |
| **HAProxy**          | routing, osrm        | `80`     | Routes `/route/v1/{profile}` and `/postcodes`, `/outcodes` |
| **OSRM frontend**    | routing, osrm        | `9966`   | Visual route planner UI                                    |
| **postcodes.io API** | routing, postcodes   | internal | UK postcode/outcode lookup                                 |
| **postcodes.io DB**  | routing, postcodes   | internal | PostgreSQL backing store                                   |
| **Airgap API**       | api                  | `5000`   | Unified FastAPI service                                    |

______________________________________________________________________

## Quick Start

**Before starting the stack**, download and process the required data (see
[Data Preparation](#data-preparation) below, or run `make prepare` from the
project root).

All commands run from the **project root**:

```bash
make up               # start everything
make geocoding-up     # Nominatim + Photon only
make nominatim-up     # Nominatim only
make routing-up       # OSRM + HAProxy + postcodes.io
make osrm-up          # OSRM + HAProxy (no postcodes)
make postcodes-up     # postcodes.io only
make api-up           # FastAPI service only
make down             # stop all services
make ps               # show running containers
make nominatim-logs   # tail logs for a service
```

Or with `docker compose` directly:

```bash
docker compose -f docker/docker-compose.yml --env-file .env --profile all up -d
docker compose -f docker/docker-compose.yml --env-file .env --profile nominatim up -d
```

______________________________________________________________________

## Data Preparation

Run the preparation CLI from the project root before starting any service:

```bash
make prepare                       # download and process all services
make prepare ARGS="--cleanup"      # remove PBF copies from OSRM dirs after processing
make prepare ARGS="--skip-photon"  # skip the ~60 GB Photon download
```

Or run the CLI directly:

```bash
uv run prepare-data --help
uv run prepare-data --cleanup --skip-photon
```

| Service          | What it needs                                                                                          | Approx. size               |
| ---------------- | ------------------------------------------------------------------------------------------------------ | -------------------------- |
| **Nominatim**    | `${PBF_REGION}-latest.osm.pbf` in `nominatim/data/`; import runs on first `docker compose up` (2–6 hr) | ~1.2 GB                    |
| **OSRM**         | Pre-processed graph files in `osrm/data/{car,foot,bike}/`                                              | ~1.2 GB + ~10 GB processed |
| **Photon**       | European dataset downloaded into `photon-data/`                                                        | ~60 GB                     |
| **postcodes.io** | None — data is pre-loaded in the DB image                                                              | —                          |

______________________________________________________________________

## Application Configuration

Set the following variables in the project root `.env` file:

| Variable        | Local value             | Description                                                                                |
| --------------- | ----------------------- | ------------------------------------------------------------------------------------------ |
| `PHOTON_API`    | `http://localhost:2322` | Photon reverse geocoding                                                                   |
| `NOMINATIM_URL` | `http://localhost:8080` | Nominatim geocoding                                                                        |
| `OSRM_API`      | `http://localhost:80`   | OSRM routing via HAProxy                                                                   |
| `POSTCODES_URL` | `http://localhost:8000` | postcodes.io - or use `http://localhost:80` to route via HAProxy                           |
| `OSRM_DATA`     | `./osrm/data`           | `car/`, `foot/`, `bike/` OSRM graph dirs (relative to `docker/`)                           |
| `OSRM_IMAGE`    | `osrm/osrm-backend`     | OSRM Docker image — override with a locally-built ARM64 image on Apple Silicon             |
| `OSRM_PLATFORM` | `linux/amd64`           | Target platform for OSRM image — set to `linux/arm64` when using a native ARM64 build      |
| `PBF_URL`       | *(Great Britain URL)*   | Full Geofabrik download URL — see [geofabrik.de](https://download.geofabrik.de)            |
| `PBF_REGION`    | `great-britain`         | Region name stem used to construct PBF/OSRM filenames (e.g. `germany`, `france`)           |

______________________________________________________________________

## Apple Silicon (ARM64)

Several images in this stack (`osrm/osrm-backend`, `osrm/osrm-frontend`,
`idealpostcodes/postcodes.io`, `idealpostcodes/postcodes.io.db`) are published
for `linux/amd64` only. Docker Desktop runs them under Rosetta 2 emulation,
which works correctly but is slower than native.

The OSRM backend is the most performance-sensitive service (CPU-heavy C++ routing
engine), so a helper script is provided to build it natively for ARM64:

```bash
# One-time build (~30 min)
./build-osrm-arm64.sh

# Then add to your project root .env:
OSRM_IMAGE=osrm-backend:arm64-local
OSRM_PLATFORM=linux/arm64
```

After that, `make prepare` and `docker compose up` will use the native image.
No changes are needed for the other amd64-only services — they run fine under
Rosetta with negligible overhead.

> **Tip:** Ensure "Use Rosetta for x86_64/amd64 emulation on Apple Silicon" is
> enabled in Docker Desktop → Settings → General (on by default in recent
> versions).

______________________________________________________________________

## Air-Gap Deployment

### 1. Save standard Docker images

On a connected machine, pull and save each image:

```bash
IMAGES=(
  "mediagis/nominatim:5.2"
  "osrm/osrm-backend"
  "osrm/osrm-frontend:latest"
  "haproxy"
  "idealpostcodes/postcodes.io:latest"
  "idealpostcodes/postcodes.io.db:latest"
)

for IMAGE in "${IMAGES[@]}"; do
  FILENAME=$(echo "${IMAGE}" | tr '/:' '_').tar
  docker pull "${IMAGE}"
  docker save "${IMAGE}" -o "${FILENAME}"
done
```

### 2. Photon - special case (large dataset)

Photon requires a ~60 GB dataset. Download it on a connected machine and bake it
into a custom image so it can be transferred as a single archive.

```bash
# a. Pull the image and let it download the European dataset
docker run --rm \
  -e REGION=europe \
  -e INITIAL_DOWNLOAD=TRUE \
  -v $(pwd)/photon-data:/photon/data \
  rtuszik/photon-docker:latest

# b. Create Dockerfile.airgap (not committed to version control)
cat > Dockerfile.airgap <<'EOF'
FROM rtuszik/photon-docker:latest
COPY ./photon-data /photon/data
ENV INITIAL_DOWNLOAD=FALSE
ENV UPDATE_STRATEGY=DISABLED
EOF

# c. Build the custom image
docker build -t photon-europe-airgap:latest -f Dockerfile.airgap .

# d. Save the image
docker save photon-europe-airgap:latest -o photon-europe-airgap.tar
```

On the air-gapped host, update the `photon` service image in
`docker/docker-compose.yml` to `photon-europe-airgap:latest`.

### 3. Download OSM PBF data for Nominatim and OSRM

Set `PBF_URL` and `PBF_REGION` in your `.env` file for the desired region, then run
`make prepare` (or `uv run prepare-data`). To download manually:

```bash
wget https://download.geofabrik.de/europe/great-britain-latest.osm.pbf
```

Browse [https://download.geofabrik.de](https://download.geofabrik.de) to find the URL
for a different region.

Copy the `.pbf` file to `docker/nominatim/data/` for Nominatim.

For OSRM, pre-process the file for each profile (see
[`osrm/README.md`](osrm/README.md) for the full extract/partition/customise
commands).

### 4. Transfer files to the air-gapped host

Transfer via USB drive, secure file copy, or your organisation's approved method:

- All `.tar` image archives
- `docker/nominatim/data/${PBF_REGION}-latest.osm.pbf`
- Pre-processed OSRM graph directories (`car/`, `foot/`, `bike/`)
- This repository (or just the `docker/` tree + `.env`)

### 5. Load images on the air-gapped host

```bash
for TAR in *.tar; do
  docker load -i "${TAR}"
done
```

### 6. Start the services

```bash
make up               # all services
make geocoding-up     # Nominatim + Photon only
make routing-up       # OSRM + HAProxy + postcodes.io
```
