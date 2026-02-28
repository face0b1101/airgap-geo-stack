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

On a connected machine, download and pre-process the Great Britain PBF extract for
each profile:

```bash
PBF=great-britain-latest.osm.pbf
wget https://download.geofabrik.de/europe/${PBF}

for PROFILE in car foot bike; do
  mkdir -p /path/to/osrm-data/${PROFILE}
  cp ${PBF} /path/to/osrm-data/${PROFILE}/

  docker run --rm -t \
    -v /path/to/osrm-data/${PROFILE}:/data \
    osrm/osrm-backend osrm-extract -p /opt/${PROFILE}.lua /data/${PBF}

  docker run --rm -t \
    -v /path/to/osrm-data/${PROFILE}:/data \
    osrm/osrm-backend osrm-partition /data/great-britain-latest.osrm

  docker run --rm -t \
    -v /path/to/osrm-data/${PROFILE}:/data \
    osrm/osrm-backend osrm-customize /data/great-britain-latest.osrm
done
```

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
