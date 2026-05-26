"""FastAPI application factory and health endpoint for the airgap geo API."""

from __future__ import annotations

import asyncio
import time
from contextlib import asynccontextmanager
from typing import Literal

import httpx
from fastapi import APIRouter, FastAPI, Request
from pydantic import BaseModel

from airgap_geo.settings import (
    NOMINATIM_URL,
    OSRM_API,
    PHOTON_API,
    POSTCODES_URL,
)
from airgap_geo_api.routers import geocode, postcodes, routing

# ---------------------------------------------------------------------------
# Health models
# ---------------------------------------------------------------------------

_ServiceStatus = Literal["up", "down"]


class ServiceHealth(BaseModel):
    """Health status for a single upstream service."""

    status: _ServiceStatus
    latency_ms: float | None = None
    detail: str | None = None


class HealthStatus(BaseModel):
    """Aggregated health status for all upstream services."""

    status: Literal["healthy", "degraded", "unhealthy"]
    services: dict[str, ServiceHealth]


# ---------------------------------------------------------------------------
# Lifespan: shared httpx.AsyncClient
# ---------------------------------------------------------------------------


@asynccontextmanager
async def _lifespan(app: FastAPI):
    """Open a single shared httpx.AsyncClient for the application lifetime."""
    async with httpx.AsyncClient() as client:
        app.state.http_client = client
        yield


# ---------------------------------------------------------------------------
# Health helpers
# ---------------------------------------------------------------------------


async def _probe(client: httpx.AsyncClient, url: str) -> ServiceHealth:
    """Make a lightweight GET probe and return a ServiceHealth result."""
    start = time.monotonic()
    try:
        response = await client.get(url, timeout=3.0)
        latency_ms = (time.monotonic() - start) * 1000
        if response.is_success:
            return ServiceHealth(status="up", latency_ms=round(latency_ms, 1))
        return ServiceHealth(
            status="down",
            latency_ms=round(latency_ms, 1),
            detail=f"HTTP {response.status_code}",
        )
    except Exception as exc:
        latency_ms = (time.monotonic() - start) * 1000
        return ServiceHealth(
            status="down",
            latency_ms=round(latency_ms, 1),
            detail=str(exc),
        )


# ---------------------------------------------------------------------------
# Health router
# ---------------------------------------------------------------------------

health_router = APIRouter(tags=["health"])


@health_router.get("/health", response_model=HealthStatus, summary="Service health")
async def health(request: Request) -> HealthStatus:
    """Check the health of all upstream backends.

    Probes each service concurrently and returns per-service status, latency,
    and an overall status of ``healthy`` (all up), ``degraded`` (some up), or
    ``unhealthy`` (all down).
    """
    client: httpx.AsyncClient = request.app.state.http_client

    probes = {
        "nominatim": f"{NOMINATIM_URL}/status.php",
        "photon": f"{PHOTON_API}/api?q=london&limit=1",
        "osrm": f"{OSRM_API}/route/v1/driving/-0.1276,51.5034;-0.1276,51.5034",
        "postcodes_io": f"{POSTCODES_URL}/postcodes/SW1A2AA",
    }

    results = await asyncio.gather(*[_probe(client, url) for url in probes.values()])
    services = dict(zip(probes.keys(), results, strict=True))

    up_count = sum(1 for s in services.values() if s.status == "up")
    total = len(services)

    if up_count == total:
        overall = "healthy"
    elif up_count == 0:
        overall = "unhealthy"
    else:
        overall = "degraded"

    return HealthStatus(status=overall, services=services)


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Airgap Geocoding API",
        description=(
            "Self-hosted, air-gapped geocoding, reverse geocoding, routing, "
            "and UK postcode lookup."
        ),
        version="1.5.1",
        lifespan=_lifespan,
    )

    app.include_router(health_router)
    app.include_router(geocode.router)
    app.include_router(routing.router)
    app.include_router(postcodes.router)

    return app
