# Nominatim

Forward geocoding service: converts place names, addresses, and postcodes into
latitude/longitude coordinates.

- **Image**: `mediagis/nominatim:5.2`
- **Port**: `8080`
- **Data import**: OSM PBF extract (controlled by `PBF_REGION`) + GB postcode dataset

## Usage

```bash
cd docker/nominatim
docker compose --env-file ../../.env up -d
```

## Data preparation

Download the OSM extract for your chosen region before first start. Set `PBF_REGION`
in your `.env` file (browse [https://download.geofabrik.de](https://download.geofabrik.de)
for available regions), then run `make prepare` from the project root, or download manually:

```bash
wget -P ./data https://download.geofabrik.de/europe/great-britain-latest.osm.pbf
```

### GB postcodes (pre-downloaded for air-gap)

The GB postcode dataset improves geocoding accuracy for UK postcodes. Rather than
letting the container download it at runtime (via SCP to a Hetzner mirror),
`make prepare` fetches it ahead of time:

```bash
# Included in `make prepare`, or download manually:
wget -P ./data https://nominatim.org/data/gb_postcodes.csv.gz
```

The compose file sets `IMPORT_GB_POSTCODES` to the container-internal path
(`/nominatim/data/gb_postcodes.csv.gz`) so Nominatim symlinks the local file
instead of attempting a network download.

## PostgreSQL tuning

The `mediagis/nominatim:5.2` image ships with PostgreSQL defaults tuned for
large servers (e.g. `maintenance_work_mem = 10GB`). The compose file overrides
these for machines with ~25 GB RAM running multiple services:

| Variable                        | Image default | Override | Notes                                    |
| ------------------------------- | ------------- | -------- | ---------------------------------------- |
| `POSTGRES_SHARED_BUFFERS`       | `2GB`         | `1GB`    | Shared buffer pool                       |
| `POSTGRES_MAINTENANCE_WORK_MEM` | `10GB`        | `2GB`    | Used during index creation (crash cause) |
| `POSTGRES_AUTOVACUUM_WORK_MEM`  | `2GB`         | `512MB`  | Per-autovacuum worker                    |
| `POSTGRES_WORK_MEM`             | `50MB`        | `32MB`   | Per-operation sort/hash memory           |
| `POSTGRES_EFFECTIVE_CACHE_SIZE` | `24GB`        | `4GB`    | Planner hint (not allocated)             |

`shm_size` is set to `4g` (up from `1g`) to give PostgreSQL ample shared memory
headroom during the index-creation phase.

Increase these values if Nominatim is the only service running on a dedicated
machine with more RAM.

## Import

The first `docker compose up` will import the data into the PostgreSQL volume
(`nominatim-data`). This takes approximately 2–6 hours depending on hardware.
Subsequent starts use the pre-built volume and are fast.

`FREEZE=true` disables incremental updates — appropriate for static air-gapped
deployments.

## Recovering from a failed import

If the import crashes (e.g. OOM during index creation), the volumes will contain
a partially-imported database. Delete them and restart:

```bash
docker compose -f docker/docker-compose.yml --profile nominatim down
docker volume rm docker_nominatim-data docker_nominatim-flatnode
docker compose -f docker/docker-compose.yml --env-file ../.env --profile nominatim up -d
```

## Verifying

```bash
curl "http://localhost:8080/search?q=10+Downing+Street+London&format=jsonv2&limit=1"
```
