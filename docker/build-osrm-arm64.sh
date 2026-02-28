#!/usr/bin/env bash
# Builds osrm-backend natively for ARM64 (Apple Silicon).
#
# The official osrm/osrm-backend image is amd64-only, so Docker Desktop runs it
# under Rosetta 2 emulation. This script builds a native ARM64 image from source
# for better performance — especially during data preparation (extract / partition
# / customise), which is heavily CPU-bound.
#
# After building, add these lines to your project root .env:
#   OSRM_IMAGE=osrm-backend:arm64-local
#   OSRM_PLATFORM=linux/arm64
#
# Usage:
#   ./build-osrm-arm64.sh [--tag TAG]
#
# Options:
#   --tag TAG   Docker image tag (default: osrm-backend:arm64-local)
#   -h, --help  Show this help message

set -euo pipefail

TAG="osrm-backend:arm64-local"
CLONE_DIR="$(mktemp -d)"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --tag)  TAG="$2"; shift ;;
    -h|--help)
      sed -n '/^# Usage:/,/^[^#]/p' "$0" | grep '^#' | sed 's/^# \{0,1\}//'
      exit 0
      ;;
    *) echo "Unknown option: $1" >&2; exit 1 ;;
  esac
  shift
done

cleanup() { rm -rf "${CLONE_DIR}"; }
trap cleanup EXIT

echo "Cloning osrm-backend source..."
git clone --depth 1 https://github.com/Project-OSRM/osrm-backend.git "${CLONE_DIR}"

echo ""
echo "Building ${TAG} for linux/arm64 (this may take 20-40 minutes)..."
docker build --platform linux/arm64 -t "${TAG}" -f "${CLONE_DIR}/docker/Dockerfile-debian" "${CLONE_DIR}"

echo ""
echo "Done — image tagged as: ${TAG}"
echo ""
echo "Add the following to your project root .env file:"
echo "  OSRM_IMAGE=${TAG}"
echo "  OSRM_PLATFORM=linux/arm64"
