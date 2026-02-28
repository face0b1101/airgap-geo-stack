# Photon

Reverse geocoding service: converts latitude/longitude coordinates into rich OSM
address properties.

- **Image**: `rtuszik/photon-docker:latest`
- **Port**: `2322`

## Usage

```bash
cd docker/photon
docker compose up -d
```

On first start, if `INITIAL_DOWNLOAD=TRUE` is set, the container will attempt to
download the ~60 GB European dataset. For air-gapped deployments, download the data
on a connected machine and bake it into a custom image instead - see
[`../README.md`](../README.md) for the full procedure.

## Air-gap image (pre-baked data)

On a connected machine:

```bash
# 1. Pull the base image and let it download the dataset
docker run --rm -e REGION=europe -e INITIAL_DOWNLOAD=TRUE \
  -v $(pwd)/photon-data:/photon/data \
  rtuszik/photon-docker:latest

# 2. Build a custom image with data baked in
docker build -t photon-europe-airgap:latest -f Dockerfile.airgap .

# 3. Save the image for transfer
docker save photon-europe-airgap:latest | gzip > photon-europe-airgap.tar.gz
```

`Dockerfile.airgap` (kept out of version control, create locally):

```dockerfile
FROM rtuszik/photon-docker:latest
COPY ./photon-data /photon/data
ENV INITIAL_DOWNLOAD=FALSE
ENV UPDATE_STRATEGY=DISABLED
```

On the air-gapped host, update `docker-compose.yml` to use
`photon-europe-airgap:latest` and load the image with:

```bash
docker load -i photon-europe-airgap.tar.gz
```

## Verifying

```bash
curl "http://localhost:2322/reverse?lat=51.5034&lon=-0.1276"
```
