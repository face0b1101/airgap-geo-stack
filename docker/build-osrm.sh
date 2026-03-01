#!/usr/bin/env bash
# Builds osrm-backend from source for a given platform.
#
# The official osrm/osrm-backend Docker Hub image is v5.26.0 (amd64-only) and
# 4+ years old.  This script builds v6.0.0 from the upstream master branch for
# any platform — use linux/arm64 for native Apple Silicon performance during
# data preparation, and linux/amd64 for export to x86_64 servers.
#
# Usage:
#   ./build-osrm.sh [--platform PLATFORM] [--tag TAG]
#
# Options:
#   --platform PLATFORM  Target platform (default: linux/arm64)
#   --tag TAG            Docker image tag (default: derived from platform,
#                        e.g. osrm-backend:arm64-local or osrm-backend:amd64-local)
#   -h, --help           Show this help message
#
# Examples:
#   ./build-osrm.sh                                # linux/arm64 → osrm-backend:arm64-local
#   ./build-osrm.sh --platform linux/amd64         # linux/amd64 → osrm-backend:amd64-local
#   ./build-osrm.sh --platform linux/amd64 --tag my-osrm:latest

set -euo pipefail

PLATFORM="linux/arm64"
TAG=""
CLONE_DIR="$(mktemp -d)"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --platform) PLATFORM="$2"; shift ;;
    --tag)      TAG="$2"; shift ;;
    -h|--help)
      sed -n '/^# Usage:/,/^[^#]/p' "$0" | grep '^#' | sed 's/^# \{0,1\}//'
      exit 0
      ;;
    *) echo "Unknown option: $1" >&2; exit 1 ;;
  esac
  shift
done

# Derive tag from platform when not explicitly provided.
if [[ -z "${TAG}" ]]; then
  ARCH="${PLATFORM#*/}"          # e.g. "arm64" from "linux/arm64"
  TAG="osrm-backend:${ARCH}-local"
fi

cleanup() { rm -rf "${CLONE_DIR}"; }
trap cleanup EXIT

echo "Cloning osrm-backend source..."
git clone --depth 1 https://github.com/Project-OSRM/osrm-backend.git "${CLONE_DIR}"

# Detect cross-compilation (target arch differs from host).  QEMU emulation
# breaks GNU make's jobserver pipe FDs, which fatally breaks LTO's lto-wrapper.
# Disable LTO in that case by patching the cloned Dockerfile.
HOST_ARCH="$(uname -m)"
TARGET_ARCH="${PLATFORM#*/}"
# Normalise: uname returns "x86_64" but Docker uses "amd64"
case "${HOST_ARCH}" in
  x86_64)  HOST_ARCH="amd64" ;;
  aarch64) HOST_ARCH="arm64" ;;
esac

if [[ "${TARGET_ARCH}" != "${HOST_ARCH}" ]]; then
  echo "Cross-compiling (${HOST_ARCH} → ${TARGET_ARCH}) — disabling LTO to avoid QEMU jobserver bug"
  sed -i.bak 's/-DENABLE_LTO=On/-DENABLE_LTO=Off/g' "${CLONE_DIR}/docker/Dockerfile-debian"
fi

echo ""
echo "Building ${TAG} for ${PLATFORM} (this may take a while)..."
docker build --platform "${PLATFORM}" -t "${TAG}" -f "${CLONE_DIR}/docker/Dockerfile-debian" "${CLONE_DIR}"

echo ""
echo "Done — image tagged as: ${TAG}"
echo ""
echo "For local development, add to your .env:"
echo "  OSRM_IMAGE=${TAG}"
echo "  OSRM_PLATFORM=${PLATFORM}"
