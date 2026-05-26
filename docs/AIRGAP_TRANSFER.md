# Air-Gap Transfer Guide

How to export the fully-processed airgap-geo-stack to a USB drive and import
it on an air-gapped machine — with zero re-processing, re-downloading, or
multi-hour Nominatim imports.

______________________________________________________________________

## Prerequisites

| Requirement              | Details                                                         |
| ------------------------ | --------------------------------------------------------------- |
| **Source machine**       | Docker running, all services up and healthy (`make status`)     |
| **Data fully processed** | `make prepare` completed; Nominatim has finished its first boot |
| **USB drive**            | 256 GB+ (exFAT recommended for cross-platform support)          |
| **Target machine**       | Docker and Docker Compose installed, no internet required       |

______________________________________________________________________

## What gets transferred

| Component                    | Source location          | Approx. size (GB UK) | Storage type                    |
| ---------------------------- | ------------------------ | -------------------- | ------------------------------- |
| Docker image tarballs        | saved during export      | 10–15 GB             | files on USB                    |
| Nominatim imported database  | Docker volume            | ~20 GB               | **Docker volume** (must export) |
| OSRM processed graphs        | `docker/osrm/data/`      | ~28 GB               | bind-mount directory            |
| Photon dataset               | `docker/photon-data/`    | ~44 GB               | bind-mount directory            |
| Nominatim PBF + UK postcodes | `docker/nominatim/data/` | ~2 GB                | bind-mount directory            |
| Project repo + `.env`        | project root             | < 100 MB             | files                           |
| **Total**                    |                          | **~105–120 GB**      |                                 |

> **Critical**: The Nominatim imported database lives in Docker volumes
> (`nominatim-data`, `nominatim-flatnode`), **not** on the filesystem. If you
> skip the volume export, Nominatim will re-import from the PBF on first boot
> (2–6 hours for Great Britain).

______________________________________________________________________

## Part 1 — Export (connected machine)

All commands assume you are in the **project root**
(`/path/to/airgap-geo-stack`). Replace paths and device names to match your
environment.

### Step 0 — Format the USB drive (macOS)

Find your USB device:

```bash
diskutil list
```

Format it as exFAT (replace `/dev/diskN` with your device):

> **Warning** — this erases all data on the drive.

```bash
diskutil eraseDisk ExFAT AIRGAPGEO /dev/diskN
```

### Step 1 — Set variables and create directories

#### bash / zsh

```bash
USB=/Volumes/AIRGAPGEO
IMGDIR="$USB/airgap-geo-stack/images"
DATADIR="$USB/airgap-geo-stack/data"
PROJ="$(pwd)"

mkdir -p "$IMGDIR" "$DATADIR"
```

#### fish

```fish
set USB /Volumes/AIRGAPGEO
set IMGDIR $USB/airgap-geo-stack/images
set DATADIR $USB/airgap-geo-stack/data
set PROJ (pwd)

mkdir -p $IMGDIR $DATADIR
```

### Step 2 — Save Docker images as tarballs

#### bash / zsh

```bash
docker save mediagis/nominatim:5.2                    -o "$IMGDIR/mediagis_nominatim_5.2.tar"
docker save osrm-backend:amd64-local                  -o "$IMGDIR/osrm-backend_amd64-local.tar"
docker save osrm/osrm-frontend:latest                 -o "$IMGDIR/osrm_osrm-frontend_latest.tar"
docker save haproxy                                    -o "$IMGDIR/haproxy.tar"
docker save idealpostcodes/postcodes.io:latest         -o "$IMGDIR/idealpostcodes_postcodes.io_latest.tar"
docker save idealpostcodes/postcodes.io.db:latest      -o "$IMGDIR/idealpostcodes_postcodes.io.db_latest.tar"
docker save rtuszik/photon-docker:latest               -o "$IMGDIR/rtuszik_photon-docker_latest.tar"
```

#### fish

```fish
docker save mediagis/nominatim:5.2                    -o $IMGDIR/mediagis_nominatim_5.2.tar
docker save osrm-backend:amd64-local                  -o $IMGDIR/osrm-backend_amd64-local.tar
docker save osrm/osrm-frontend:latest                 -o $IMGDIR/osrm_osrm-frontend_latest.tar
docker save haproxy                                    -o $IMGDIR/haproxy.tar
docker save idealpostcodes/postcodes.io:latest         -o $IMGDIR/idealpostcodes_postcodes.io_latest.tar
docker save idealpostcodes/postcodes.io.db:latest      -o $IMGDIR/idealpostcodes_postcodes.io.db_latest.tar
docker save rtuszik/photon-docker:latest               -o $IMGDIR/rtuszik_photon-docker_latest.tar
```

> **OSRM image tag**: If you used a different `OSRM_IMAGE` value in `.env`
> (e.g. `osrm/osrm-backend` instead of a locally-built tag), replace
> `osrm-backend:amd64-local` above with that value.

#### Build and save the FastAPI API image

```bash
docker compose -f docker/docker-compose.yml --env-file .env build api
docker images | grep api
```

Save it (adjust the tag if Compose named it differently):

#### bash / zsh

```bash
docker save docker-api:latest -o "$IMGDIR/airgap-api.tar"
```

#### fish

```fish
docker save docker-api:latest -o $IMGDIR/airgap-api.tar
```

### Step 3 — Export the Nominatim database volume

First, find the exact volume names (they are prefixed with the Compose project
name, typically `docker`):

```bash
docker volume ls | grep nominatim
```

Expected output:

```text
local     docker_nominatim-data
local     docker_nominatim-flatnode
```

Adjust the volume names in the commands below if yours differ.

> **macOS / Colima users**: Do **not** use `docker run -v /Volumes/...:/backup`
> to write directly to the USB. On Colima (and other Lima-based Docker setups),
> only `/Users/$USER` is shared into the VM — `/Volumes` is not. Bind-mounting a
> `/Volumes/...` path will silently write to the VM's root disk instead of the
> USB, filling it up. The `docker cp` approach below streams data to the **host
> side** (your Mac) and avoids this entirely.

#### bash / zsh

```bash
# Export the PostgreSQL database (~20 GB → ~5–8 GB gzipped)
docker run -d --name nominatim-export \
  -v docker_nominatim-data:/source:ro \
  alpine sleep 3600
docker cp nominatim-export:/source - | gzip > "$DATADIR/nominatim-data.tar.gz"
docker rm -f nominatim-export

# Export the flatnode file (usually empty / negligible)
docker run -d --name flatnode-export \
  -v docker_nominatim-flatnode:/source:ro \
  alpine sleep 3600
docker cp flatnode-export:/source - | gzip > "$DATADIR/nominatim-flatnode.tar.gz"
docker rm -f flatnode-export
```

#### fish

```fish
docker run -d --name nominatim-export \
  -v docker_nominatim-data:/source:ro \
  alpine sleep 3600
docker cp nominatim-export:/source - | gzip > $DATADIR/nominatim-data.tar.gz
docker rm -f nominatim-export

docker run -d --name flatnode-export \
  -v docker_nominatim-flatnode:/source:ro \
  alpine sleep 3600
docker cp flatnode-export:/source - | gzip > $DATADIR/nominatim-flatnode.tar.gz
docker rm -f flatnode-export
```

`docker cp` streams a tar archive to stdout on the **client** (your Mac).
Piping through `gzip` compresses it — PostgreSQL data typically compresses
3–4×, so the ~20 GB volume shrinks to roughly 5–8 GB.

### Step 4 — Copy data directories

#### bash / zsh

```bash
rsync -avh --progress docker/osrm/data/ "$DATADIR/osrm-data/"
rsync -avh --progress docker/nominatim/data/ "$DATADIR/nominatim-data-files/"
rsync -avh --progress docker/photon-data/ "$DATADIR/photon-data/"
```

#### fish

```fish
rsync -avh --progress docker/osrm/data/ $DATADIR/osrm-data/
rsync -avh --progress docker/nominatim/data/ $DATADIR/nominatim-data-files/
rsync -avh --progress docker/photon-data/ $DATADIR/photon-data/
```

> `rsync` is preferred over `cp` — it shows progress and can be resumed with
> the same command if interrupted.

### Step 5 — Copy the project repo and config

#### bash / zsh

```bash
rsync -avh --progress \
  --exclude='docker/osrm/data' \
  --exclude='docker/photon-data' \
  --exclude='docker/nominatim/data/*.pbf' \
  --exclude='.venv' \
  --exclude='__pycache__' \
  --exclude='.git' \
  "$PROJ/" "$USB/airgap-geo-stack/repo/"

cp "$PROJ/.env" "$USB/airgap-geo-stack/repo/.env"
```

#### fish

```fish
rsync -avh --progress \
  --exclude='docker/osrm/data' \
  --exclude='docker/photon-data' \
  --exclude='docker/nominatim/data/*.pbf' \
  --exclude='.venv' \
  --exclude='__pycache__' \
  --exclude='.git' \
  $PROJ/ $USB/airgap-geo-stack/repo/

cp $PROJ/.env $USB/airgap-geo-stack/repo/.env
```

### Step 6 — Verify and eject

#### bash / zsh

```bash
echo "--- Images ---"
ls -lh "$IMGDIR/"
echo "--- Data ---"
du -sh "$DATADIR"/*/
echo "--- Repo ---"
ls "$USB/airgap-geo-stack/repo/Makefile"

diskutil eject /dev/diskN
```

#### fish

```fish
echo "--- Images ---"
ls -lh $IMGDIR/
echo "--- Data ---"
du -sh $DATADIR/*/
echo "--- Repo ---"
ls $USB/airgap-geo-stack/repo/Makefile

diskutil eject /dev/diskN
```

### USB layout after export

```text
AIRGAPGEO/
└── airgap-geo-stack/
    ├── images/
    │   ├── mediagis_nominatim_5.2.tar
    │   ├── osrm-backend_amd64-local.tar
    │   ├── osrm_osrm-frontend_latest.tar
    │   ├── haproxy.tar
    │   ├── idealpostcodes_postcodes.io_latest.tar
    │   ├── idealpostcodes_postcodes.io.db_latest.tar
    │   ├── rtuszik_photon-docker_latest.tar
    │   └── airgap-api.tar
    ├── data/
    │   ├── nominatim-data.tar.gz       ← Docker volume export (~5–8 GB compressed)
    │   ├── nominatim-flatnode.tar.gz   ← Docker volume export (small)
    │   ├── nominatim-data-files/       ← PBF + postcodes (~2 GB)
    │   ├── osrm-data/                  ← car/ foot/ bike/ (~28 GB)
    │   └── photon-data/                ← Photon index (~44 GB)
    └── repo/
        ├── .env
        ├── Makefile
        ├── docker/
        │   └── docker-compose.yml
        ├── src/
        └── ...
```

______________________________________________________________________

## Part 2 — Import (air-gapped machine)

All commands assume the USB drive is mounted. Adjust the mount point for your
OS (e.g. `/media/AIRGAPGEO` on Linux, `/Volumes/AIRGAPGEO` on macOS).

### Step 7 — Set variables

#### bash / zsh

```bash
USB=/media/AIRGAPGEO          # adjust for your OS
IMGDIR="$USB/airgap-geo-stack/images"
DATADIR="$USB/airgap-geo-stack/data"
REPO="$USB/airgap-geo-stack/repo"
```

#### fish

```fish
set USB /media/AIRGAPGEO      # adjust for your OS
set IMGDIR $USB/airgap-geo-stack/images
set DATADIR $USB/airgap-geo-stack/data
set REPO $USB/airgap-geo-stack/repo
```

### Step 8 — Load Docker images

#### bash / zsh

```bash
for TAR in "$IMGDIR"/*.tar; do
  echo "Loading $TAR ..."
  docker load -i "$TAR"
done
```

#### fish

```fish
for TAR in $IMGDIR/*.tar
  echo "Loading $TAR ..."
  docker load -i $TAR
end
```

### Step 9 — Restore data directories

#### bash / zsh

```bash
cd "$REPO"

rsync -avh "$DATADIR/osrm-data/"             docker/osrm/data/
rsync -avh "$DATADIR/nominatim-data-files/"   docker/nominatim/data/
rsync -avh "$DATADIR/photon-data/"            docker/photon-data/
```

#### fish

```fish
cd $REPO

rsync -avh $DATADIR/osrm-data/             docker/osrm/data/
rsync -avh $DATADIR/nominatim-data-files/   docker/nominatim/data/
rsync -avh $DATADIR/photon-data/            docker/photon-data/
```

### Step 10 — Restore Nominatim Docker volumes

Create the volumes and stream the compressed tarballs into them. The
`docker cp` approach mirrors the export and works on both native Linux and
macOS/Colima without bind-mount path issues.

#### bash / zsh

```bash
docker volume create docker_nominatim-data
docker volume create docker_nominatim-flatnode

# Restore nominatim-data
docker run -d --name nominatim-restore \
  -v docker_nominatim-data:/target \
  alpine sleep 3600
gunzip -c "$DATADIR/nominatim-data.tar.gz" | docker cp - nominatim-restore:/target
docker rm -f nominatim-restore

# Restore nominatim-flatnode
docker run -d --name flatnode-restore \
  -v docker_nominatim-flatnode:/target \
  alpine sleep 3600
gunzip -c "$DATADIR/nominatim-flatnode.tar.gz" | docker cp - flatnode-restore:/target
docker rm -f flatnode-restore
```

#### fish

```fish
docker volume create docker_nominatim-data
docker volume create docker_nominatim-flatnode

docker run -d --name nominatim-restore \
  -v docker_nominatim-data:/target \
  alpine sleep 3600
gunzip -c $DATADIR/nominatim-data.tar.gz | docker cp - nominatim-restore:/target
docker rm -f nominatim-restore

docker run -d --name flatnode-restore \
  -v docker_nominatim-flatnode:/target \
  alpine sleep 3600
gunzip -c $DATADIR/nominatim-flatnode.tar.gz | docker cp - flatnode-restore:/target
docker rm -f flatnode-restore
```

> **Native Linux shortcut**: If the target runs Docker natively (no VM), you
> can use a bind-mount instead of `docker cp`:
>
> ```bash
> docker run --rm \
>   -v docker_nominatim-data:/target \
>   -v "$DATADIR":/backup:ro \
>   alpine sh -c "gunzip -c /backup/nominatim-data.tar.gz | tar xf - -C /target"
> ```
>
> On macOS with Colima, stick with `docker cp` — see
> [Colima troubleshooting](#colima--lima-bind-mount-paths) below.

> **Volume naming**: Docker Compose prefixes volume names with the project name
> (derived from the directory name, e.g. `docker`). The volumes must match what
> `docker-compose.yml` expects. Verify with:
>
> ```bash
> docker compose -f docker/docker-compose.yml --env-file .env config | grep -A1 'volumes:'
> ```
>
> If the project prefix differs, let Compose create the volumes first, note
> their names, then restore into those:
>
> ```bash
> docker compose -f docker/docker-compose.yml --env-file .env create nominatim
> docker volume ls | grep nominatim
> ```

### Step 11 — Start the stack

```bash
cd "$REPO"    # or $REPO in fish
make up
```

Wait a couple of minutes for services to initialise, then verify:

```bash
make status
```

All five services should report healthy. No re-importing, no re-downloading.

______________________________________________________________________

## Troubleshooting

### Nominatim starts re-importing instead of using the restored volume

The volume names on the target don't match what Compose expects. Check:

```bash
docker volume ls | grep nominatim
docker compose -f docker/docker-compose.yml --env-file .env config 2>/dev/null | grep nominatim
```

Remove the mismatched volume and re-create with the correct name, then restore
the tarball again.

### OSRM backends fail to start

The OSRM graph files must have been processed with the **same OSRM version** as
the image being used at runtime. If you built `osrm-backend:amd64-local` (v6)
on the source machine, the same image must be loaded on the target. The upstream
Docker Hub image (`osrm/osrm-backend`) is v5.26 — the data formats are
incompatible between v5 and v6.

### Photon reports "no data"

Ensure `docker/photon-data/` contains the `photon_data/` subdirectory with the
Lucene index files. The compose file sets `INITIAL_DOWNLOAD=FALSE`, so Photon
will not attempt to download anything — it expects data to already be present.

### USB filesystem errors or file size limits

exFAT supports files up to 16 EB and is readable on macOS, Linux, and Windows
without extra drivers. If your USB is formatted as FAT32, individual files are
capped at 4 GB — the Nominatim volume tarball and image tarballs will fail.
Reformat as exFAT.

### Checking image architectures

To verify that exported images target the correct platform:

```bash
docker inspect --format='{{.Os}}/{{.Architecture}}' mediagis/nominatim:5.2
```

All images should show `linux/amd64` if your `.env` has
`FORCE_PLATFORM=linux/amd64`.

______________________________________________________________________

## Colima / Lima notes

If you run Docker via [Colima](https://github.com/abiosoft/colima) (common on
macOS), be aware of these VM-specific gotchas.

### Colima / Lima bind-mount paths

Colima (via Lima) only shares **`/Users/$USER`** into the VM by default.
Paths like `/Volumes/...` (USB drives), `/tmp`, and `/opt` are **not** shared —
they resolve to directories on the VM's root disk.

This means `docker run -v /Volumes/MYUSB:/backup ...` will silently write to
the VM's root filesystem, not to the USB drive. It will eventually fail with
"no space left on device" once the VM root disk fills up.

**Solution**: Use `docker cp` to stream data to/from the **client side** (your
Mac) for any path that isn't under `/Users/$USER`. This is why the export and
import steps above use `docker cp` with pipes rather than bind mounts.

### Colima root disk full

Colima's VM has a small root disk (often ~20 GB) separate from its data disk.
Docker and containerd data may land on root instead of the larger data disk.

Check:

```bash
colima ssh -- df -h /
```

If root is full:

1. **Find what's using space** (the `-x` flag stays on the root filesystem):

```bash
colima ssh
sudo du -xsh /* 2>/dev/null | sort -rh | head -10
```

2. **Move Docker and containerd to the data disk**:

```bash
# Inside the VM (colima ssh):
sudo systemctl stop docker containerd

sudo mv /var/lib/docker /mnt/lima-colima/docker
sudo ln -s /mnt/lima-colima/docker /var/lib/docker

sudo mv /var/lib/containerd /mnt/lima-colima/containerd
sudo ln -s /mnt/lima-colima/containerd /var/lib/containerd

sudo systemctl start containerd docker
```

3. **Ensure `/tmp` exists** (Docker needs it to create containers):

```bash
# Inside the VM:
sudo mkdir -p /tmp
sudo chmod 1777 /tmp
```

4. **Clean up any stale data** written to `/Volumes/...` inside the VM by
   failed export attempts:

```bash
# Inside the VM:
sudo du -xsh /Volumes/* 2>/dev/null
sudo rm -rf /Volumes/AIRGAPGEO   # if present — this is stale VM data, not your USB
```
