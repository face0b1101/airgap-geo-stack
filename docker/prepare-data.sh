#!/usr/bin/env bash
# Prepares all data required by the airgap-geo-stack Docker services.
#
# Downloads an OSM PBF extract once (controlled by PBF_URL / PBF_REGION) and
# distributes it to:
#   - nominatim/data/   (Nominatim imports on first docker compose up)
#   - osrm/data/{car,foot,bike}/  (extract/partition/customise runs here)
#
# Also downloads the Photon European dataset (~60 GB).
#
# Set PBF_URL and PBF_REGION in your .env file to change the region. Browse
# https://download.geofabrik.de to find your extract. For example:
#   PBF_URL=https://download.geofabrik.de/europe/germany-latest.osm.pbf
#   PBF_REGION=germany
#
# Memory requirements: osrm-extract for large extracts (e.g. Great Britain)
# needs ~10-14 GB RAM. Docker Desktop on macOS must be given at least 12 GB
# in Settings → Resources. Colima users: colima stop && colima start --memory 16
# If you cannot increase Docker's RAM, pass --threads 1 to halve peak usage
# (the extract will be slower but should complete within ~6 GB).
#
# Usage:
#   ./prepare-data.sh [OPTIONS]
#
# Options:
#   --cleanup          Delete PBF copies from OSRM profile dirs after processing
#   --force            Re-run all stages even if output files already exist
#   --skip-nominatim   Skip the PBF download step for Nominatim
#   --skip-osrm        Skip OSRM extract/partition/customise
#   --skip-photon      Skip the Photon dataset download
#   --threads N        Number of threads for osrm-extract (default: 4).
#                      Use --threads 1 on machines with limited RAM (~6 GB Docker limit).
#   -h, --help         Show this help message

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PBF_REGION="${PBF_REGION:-great-britain}"
PBF="${PBF_REGION}-latest.osm.pbf"
PBF_URL="${PBF_URL:-https://download.geofabrik.de/europe/${PBF}}"

CLEANUP=false
FORCE=false
SKIP_NOMINATIM=false
SKIP_OSRM=false
SKIP_PHOTON=false
OSRM_THREADS=4

# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------
while [[ $# -gt 0 ]]; do
  case "$1" in
    --cleanup)          CLEANUP=true ;;
    --force)            FORCE=true ;;
    --skip-nominatim)   SKIP_NOMINATIM=true ;;
    --skip-osrm)        SKIP_OSRM=true ;;
    --skip-photon)      SKIP_PHOTON=true ;;
    --threads)
      shift
      OSRM_THREADS="${1:?--threads requires a value}"
      ;;
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
    OSRM_BASE="${DIR}/${PBF_REGION}-latest.osrm"
    mkdir -p "${DIR}"

    echo ""
    echo "=== OSRM profile: ${PROFILE} ==="

    if [[ "$FORCE" == false && -f "${OSRM_BASE}.mldgr" ]]; then
      echo "Profile ${PROFILE} already complete (found .osrm.mldgr), skipping."
      continue
    fi

    if [[ ! -f "${DIR}/${PBF}" ]]; then
      echo "Copying PBF to ${DIR}/"
      cp "${SCRIPT_DIR}/nominatim/data/${PBF}" "${DIR}/"
    fi

    if [[ "$FORCE" == false && -f "${OSRM_BASE}" ]]; then
      echo "Extract already done for ${PROFILE}, skipping."
    else
      echo "Extracting (${PROFILE}) with ${OSRM_THREADS} thread(s)..."
      docker run --rm -t \
        --platform "${OSRM_PLATFORM:-linux/amd64}" \
        -v "${DIR}:/data" \
        "${OSRM_IMAGE:-osrm/osrm-backend}" osrm-extract -t "${OSRM_THREADS}" -p "/opt/${PROFILE}.lua" "/data/${PBF}"
    fi

    if [[ "$FORCE" == false && -f "${OSRM_BASE}.partition" ]]; then
      echo "Partition already done for ${PROFILE}, skipping."
    else
      echo "Partitioning (${PROFILE})..."
      docker run --rm -t \
        --platform "${OSRM_PLATFORM:-linux/amd64}" \
        -v "${DIR}:/data" \
        "${OSRM_IMAGE:-osrm/osrm-backend}" osrm-partition "/data/${PBF_REGION}-latest.osrm"
    fi

    echo "Customising (${PROFILE})..."
    docker run --rm -t \
      --platform "${OSRM_PLATFORM:-linux/amd64}" \
      -v "${DIR}:/data" \
      "${OSRM_IMAGE:-osrm/osrm-backend}" osrm-customize "/data/${PBF_REGION}-latest.osrm"

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

  if [[ "$FORCE" == false && -d "${PHOTON_DATA}/search_index" ]]; then
    echo "Photon data already present at ${PHOTON_DATA}/search_index, skipping."
  else
    docker run --rm \
      -e REGION=europe \
      -e INITIAL_DOWNLOAD=TRUE \
      -v "${PHOTON_DATA}:/photon/data" \
      rtuszik/photon-docker:latest
  fi

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
