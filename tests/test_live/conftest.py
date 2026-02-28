"""Shared fixtures for live integration tests.

These tests hit real Docker backend services (Nominatim, Photon, OSRM,
postcodes.io) and are excluded from the default pytest run.  Start the
stack with ``make up`` before running::

    uv run pytest -m live -v
"""

from __future__ import annotations

import asyncio
from collections.abc import Generator

import httpx
import pytest
from fastapi.testclient import TestClient

from airgap_geo.settings import NOMINATIM_URL, OSRM_API, PHOTON_API, POSTCODES_URL
from airgap_geo_api.app import create_app

HEALTH_URLS: dict[str, str] = {
    "nominatim": f"{NOMINATIM_URL}/status.php",
    "photon": f"{PHOTON_API}/api?q=london&limit=1",
    "osrm": f"{OSRM_API}/route/v1/driving/-0.1276,51.5034;-0.1276,51.5034",
    "postcodes_io": f"{POSTCODES_URL}/postcodes/SW1A2AA",
}


def _services_reachable() -> bool:
    """Return True if every backend service responds within 3 s."""

    async def _check() -> bool:
        async with httpx.AsyncClient() as client:
            for url in HEALTH_URLS.values():
                try:
                    r = await client.get(url, timeout=3.0)
                    if not r.is_success:
                        return False
                except Exception:
                    return False
        return True

    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(_check())
    finally:
        loop.close()


_BACKEND_UP = _services_reachable()

live = pytest.mark.live
skip_unless_live = pytest.mark.skipif(
    not _BACKEND_UP,
    reason="Docker backend services are not reachable",
)


@pytest.fixture(scope="module")
async def http_client():
    """Module-scoped async HTTP client for direct service-module tests."""
    async with httpx.AsyncClient() as client:
        yield client


@pytest.fixture()
def api_client() -> Generator[TestClient]:
    """Per-test FastAPI TestClient backed by real services (no httpx_mock)."""
    with TestClient(create_app()) as tc:
        yield tc
