#!/usr/bin/env bash
# Prepares all data required by the airgap-geocoding-stack Docker services.
#
# Downloads the Great Britain OSM PBF extract once and distributes it to:
#   - nominatim/data/   (Nominatim imports on first docker compose up)
#   - osrm/data/{car,foot,bike}/  (extract/partition/customise runs here)
#
# Also downloads the Photon European dataset (~60 GB).
#
# Usage:
#   ./prepare-data.sh [OPTIONS]
#
# Options:
#   --cleanup          Delete PBF copies from OSRM profile dirs after processing
#   --skip-nominatim   Skip the PBF download step for Nominatim
#   --skip-osrm        Skip OSRM extract/partition/customise
#   --skip-photon      Skip the Photon dataset download
#   -h, --help         Show this help message

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PBF="great-britain-latest.osm.pbf"
PBF_URL="https://download.geofabrik.de/europe/${PBF}"

CLEANUP=false
SKIP_NOMINATIM=false
SKIP_OSRM=false
SKIP_PHOTON=false

# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------
while [[ $# -gt 0 ]]; do
  case "$1" in
    --cleanup)          CLEANUP=true ;;
    --skip-nominatim)   SKIP_NOMINATIM=true ;;
    --skip-osrm)        SKIP_OSRM=true ;;
    --skip-photon)      SKIP_PHOTON=true ;;
    -h|--help)
      sed -n '/^# Usage:/,/^[^#]/p' "$0" | grep '^#' | sed 's/^# \{0,1\}//'
      exit 0
      ;;
    *) echo "Unknown option: $1" >&2; exit 1 ;;
  esac
  shift
done

# ---------------------------------------------------------------------------
# Step 1: Download PBF (shared by Nominatim and OSRM)
# ---------------------------------------------------------------------------
if [[ "$SKIP_NOMINATIM" == false || "$SKIP_OSRM" == false ]]; then
  PBF_DEST="${SCRIPT_DIR}/nominatim/data/${PBF}"
  mkdir -p "${SCRIPT_DIR}/nominatim/data"

  if [[ -f "$PBF_DEST" ]]; then
    echo "PBF already present at ${PBF_DEST}, resuming download if incomplete..."
  else
    echo "Downloading ${PBF} (~1.2 GB)..."
  fi

  wget -c -O "${PBF_DEST}" "${PBF_URL}"
  echo "PBF ready: ${PBF_DEST}"
fi

# ---------------------------------------------------------------------------
# Step 2: OSRM extract / partition / customise (three profiles)
# ---------------------------------------------------------------------------
if [[ "$SKIP_OSRM" == false ]]; then
  for PROFILE in car foot bike; do
    DIR="${SCRIPT_DIR}/osrm/data/${PROFILE}"
    mkdir -p "${DIR}"

    echo ""
    echo "=== OSRM profile: ${PROFILE} ==="

    if [[ ! -f "${DIR}/${PBF}" ]]; then
      echo "Copying PBF to ${DIR}/"
      cp "${SCRIPT_DIR}/nominatim/data/${PBF}" "${DIR}/"
    fi

    echo "Extracting (${PROFILE})..."
    docker run --rm -t \
      -v "${DIR}:/data" \
      osrm/osrm-backend osrm-extract -p "/opt/${PROFILE}.lua" "/data/${PBF}"

    echo "Partitioning (${PROFILE})..."
    docker run --rm -t \
      -v "${DIR}:/data" \
      osrm/osrm-backend osrm-partition /data/great-britain-latest.osrm

    echo "Customising (${PROFILE})..."
    docker run --rm -t \
      -v "${DIR}:/data" \
      osrm/osrm-backend osrm-customize /data/great-britain-latest.osrm

    if [[ "$CLEANUP" == true ]]; then
      echo "Removing PBF copy from ${DIR}/ (--cleanup)"
      rm "${DIR}/${PBF}"
    fi

    echo "Done: ${PROFILE}"
  done
fi

# ---------------------------------------------------------------------------
# Step 3: Photon European dataset (~60 GB)
# ---------------------------------------------------------------------------
if [[ "$SKIP_PHOTON" == false ]]; then
  echo ""
  echo "=== Photon dataset (~60 GB — this will take a while) ==="
  PHOTON_DATA="${SCRIPT_DIR}/photon-data"
  mkdir -p "${PHOTON_DATA}"

  docker run --rm \
    -e REGION=europe \
    -e INITIAL_DOWNLOAD=TRUE \
    -v "${PHOTON_DATA}:/photon/data" \
    rtuszik/photon-docker:latest

  echo ""
  echo "Photon data downloaded to ${PHOTON_DATA}/"
  echo "For air-gap deployment, build a custom image — see docker/photon/README.md"
fi

# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------
echo ""
echo "Data preparation complete."
echo "Start the stack with:"
echo "  cd docker && docker compose --env-file ../.env up -d"
