#!/usr/bin/env bash
# Smoke-test the airgap geo stack (Docker backends + FastAPI).
#
# Run from the repository root after ``make up``::
#
#   ./scripts/smoke-test.sh
#   ./scripts/smoke-test.sh --pytest   # also run ``make test-live``
#
# Exit code 0 when all probes pass; 1 otherwise.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

RUN_PYTEST=0
for arg in "$@"; do
    case "$arg" in
        --pytest) RUN_PYTEST=1 ;;
        -h | --help)
            echo "Usage: $0 [--pytest]"
            echo "  --pytest  Run make test-live after HTTP smoke checks"
            exit 0
            ;;
        *)
            echo "Unknown option: $arg" >&2
            exit 2
            ;;
    esac
done

# Load .env when present (same variables as the Python library / Makefile).
set -a
# shellcheck disable=SC1091
[ -f .env ] && source .env
set +a

PHOTON_API="${PHOTON_API:-http://localhost:2322}"
NOMINATIM_URL="${NOMINATIM_URL:-http://localhost:8080}"
OSRM_API="${OSRM_API:-http://localhost:80}"
POSTCODES_URL="${POSTCODES_URL:-http://localhost:8000}"
API_PORT="${API_PORT:-5050}"
API_BASE="http://localhost:${API_PORT}"

PASS=0
FAIL=0

pass() {
    PASS=$((PASS + 1))
    printf '  \033[32m✓\033[0m %s\n' "$1"
}

fail() {
    FAIL=$((FAIL + 1))
    printf '  \033[31m✗\033[0m %s\n' "$1"
    if [[ -n "${2:-}" ]]; then
        printf '      %s\n' "$2"
    fi
}

# probe <label> <curl args...>
probe() {
    local label="$1"
    shift
    local out http_code
    out="$(curl -sS -o /dev/null -w '%{http_code}' --connect-timeout 5 --max-time 15 "$@" 2>&1)" || {
        fail "$label" "$out"
        return
    }
    http_code="$out"
    if [[ "$http_code" =~ ^2 ]]; then
        pass "$label (HTTP $http_code)"
    else
        fail "$label" "HTTP $http_code"
    fi
}

# probe_json <label> <url> <jq filter>  (requires jq)
probe_json() {
    local label="$1" url="$2" filter="$3"
    if ! command -v jq >/dev/null 2>&1; then
        probe "$label" "$url"
        return
    fi
    local body
    if ! body="$(curl -sS --connect-timeout 5 --max-time 30 "$url" 2>&1)"; then
        fail "$label" "$body"
        return
    fi
    if echo "$body" | jq -e "$filter" >/dev/null 2>&1; then
        pass "$label"
    else
        fail "$label" "response did not match: $filter"
    fi
}

echo "Backend services"
probe "Nominatim" "${NOMINATIM_URL}/status.php"
probe "Photon" "${PHOTON_API}/api?q=london&limit=1"
probe "OSRM (driving)" \
    "${OSRM_API}/route/v1/driving/-0.1276,51.5034;-0.1276,51.5034"
probe "postcodes.io" "${POSTCODES_URL}/postcodes/SW1A2AA"

echo ""
echo "Airgap API (${API_BASE})"
probe_json "GET /health" "${API_BASE}/health" '.status == "healthy"'
probe_json "GET /geocode" \
    "${API_BASE}/geocode?q=51.5034,-0.1276" \
    '.geo.lat != null'
probe "GET /postcodes/SW1A2AA" "${API_BASE}/postcodes/SW1A2AA"

route_body='{"origin":{"lat":51.5034,"lon":-0.1276},"destination":{"lat":51.5074,"lon":-0.1278},"profile":"driving"}'
route_code="$(
    curl -sS -o /dev/null -w '%{http_code}' --connect-timeout 5 --max-time 60 \
        -X POST "${API_BASE}/route" \
        -H 'Content-Type: application/json' \
        -d "$route_body" 2>&1
)" || route_code="ERR"
if [[ "$route_code" =~ ^2 ]]; then
    pass "POST /route (HTTP $route_code)"
else
    fail "POST /route" "HTTP $route_code"
fi

echo ""
printf 'Results: %d passed, %d failed\n' "$PASS" "$FAIL"

if [[ "$FAIL" -gt 0 ]]; then
    echo "Hint: run \`make status\` for per-service detail, or \`make ps\` to check containers."
    exit 1
fi

if [[ "$RUN_PYTEST" -eq 1 ]]; then
    echo ""
    echo "Running pytest live suite (make test-live)..."
    make test-live
fi

exit 0
