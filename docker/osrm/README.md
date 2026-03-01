# OSRM + HAProxy + postcodes.io

This stack provides road routing for three profiles (driving, walking, cycling) via
OSRM backends, a HAProxy reverse proxy, the OSRM visual frontend, and UK postcode
lookup via postcodes.io.

| Service          | Container              | Port     | Role                              |
| ---------------- | ---------------------- | -------- | --------------------------------- |
| OSRM driving     | `osrm-backend-driving` | internal | Car profile routing               |
| OSRM walking     | `osrm-backend-walking` | internal | Foot profile routing              |
| OSRM cycling     | `osrm-backend-cycling` | internal | Bike profile routing              |
| HAProxy          | `osrm-haproxy`         | `80`     | Routes requests by profile / path |
| OSRM frontend    | `osrm-frontend`        | `9966`   | Visual route planner UI           |
| postcodes.io API | `postcodes-api`        | internal | UK postcode lookup                |
| postcodes.io DB  | `postcodes-db`         | internal | PostgreSQL backing store          |

## Prerequisites

Set `OSRM_DATA` in your `.env` file to the path of a directory containing
pre-processed OSRM graph files under `car/`, `foot/`, and `bike/` subdirectories.

```env
OSRM_DATA=/path/to/osrm-data
```

## Usage

```bash
cd docker/osrm
docker compose --env-file ../../.env up -d
```

## Data preparation

On a connected machine, download and pre-process the PBF extract for each profile.
Set `PBF_REGION` to your chosen region name (browse
[https://download.geofabrik.de](https://download.geofabrik.de) for options).
The commands below also use `OSRM_IMAGE` and `OSRM_PLATFORM` so that a locally-built
ARM64 image works transparently (see [Apple Silicon](#apple-silicon-arm64) below).

```bash
PBF_REGION="${PBF_REGION:-great-britain}"
PBF="${PBF_REGION}-latest.osm.pbf"
wget "https://download.geofabrik.de/europe/${PBF}"

for PROFILE in car foot bike; do
  mkdir -p /path/to/osrm-data/${PROFILE}
  cp ${PBF} /path/to/osrm-data/${PROFILE}/

  docker run --rm -t \
    --platform "${OSRM_PLATFORM:-linux/amd64}" \
    -v /path/to/osrm-data/${PROFILE}:/data \
    "${OSRM_IMAGE:-osrm/osrm-backend}" osrm-extract -p /opt/${PROFILE}.lua "/data/${PBF}"

  docker run --rm -t \
    --platform "${OSRM_PLATFORM:-linux/amd64}" \
    -v /path/to/osrm-data/${PROFILE}:/data \
    "${OSRM_IMAGE:-osrm/osrm-backend}" osrm-partition "/data/${PBF_REGION}-latest.osrm"

  docker run --rm -t \
    --platform "${OSRM_PLATFORM:-linux/amd64}" \
    -v /path/to/osrm-data/${PROFILE}:/data \
    "${OSRM_IMAGE:-osrm/osrm-backend}" osrm-customize "/data/${PBF_REGION}-latest.osrm"
done
```

## Memory requirements

`osrm-extract` for the Great Britain extract requires roughly **10–14 GB** of RAM during
the edge-expanded graph generation phase. Docker must be given at least **12 GB**:

- **Docker Desktop**: Settings → Resources → Memory
- **Colima**: `colima stop && colima start --memory 16`

If you cannot allocate that much, pass `--threads 1` to `make prepare` (via `ARGS`):

```bash
make prepare ARGS="--threads 1"
```

This halves peak memory usage (~6–8 GB) at the cost of a longer extraction time.

## Apple Silicon (ARM64)

The `osrm/osrm-backend` image is published for `linux/amd64` only. On Apple
Silicon it runs under Rosetta 2 emulation, which is functional but slower —
especially during the CPU-heavy extract/partition/customise steps above.

To build from source for any platform, set `OSRM_IMAGE` and `OSRM_PLATFORM` in
your `.env` and run:

```bash
make osrm-build   # uses OSRM_IMAGE / OSRM_PLATFORM from .env
```

Or invoke the script directly:

```bash
../build-osrm.sh                          # linux/arm64 → osrm-backend:arm64-local
../build-osrm.sh --platform linux/amd64   # linux/amd64 → osrm-backend:amd64-local
```

The other amd64-only services in this stack (`osrm-frontend`, `postcodes.io`,
`postcodes.io.db`) run fine under emulation with negligible overhead.

## HAProxy routing rules

| Path prefix           | Backend                     |
| --------------------- | --------------------------- |
| `/route/v1/driving/*` | `osrm-backend-driving:5000` |
| `/route/v1/walking/*` | `osrm-backend-walking:5000` |
| `/route/v1/cycling/*` | `osrm-backend-cycling:5000` |
| `/postcodes/*`        | `postcodes-api:8000`        |
| `/outcodes/*`         | `postcodes-api:8000`        |

## Verifying

```bash
# Driving route
curl "http://localhost:80/route/v1/driving/-0.1276,51.5034;-2.2426,53.4808?steps=false&overview=full"

# Postcode lookup
curl "http://localhost:80/postcodes/SW1A2AA"
```
