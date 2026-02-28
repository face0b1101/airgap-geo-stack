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

The first `docker compose up` will import the data into the PostgreSQL volume
(`nominatim-data`). This takes approximately 2–6 hours depending on hardware.
Subsequent starts use the pre-built volume and are fast.

`FREEZE=true` disables incremental updates - appropriate for static air-gapped
deployments.

## Verifying

```bash
curl "http://localhost:8080/search?q=10+Downing+Street+London&format=jsonv2&limit=1"
```
