"""Routing helpers backed by OSRM via HAProxy."""

from __future__ import annotations

import httpx

from airgap_geo.models import GeoPoint, RouteResult, RouteStep
from airgap_geo.settings import OSRM_API

_VALID_PROFILES = {"driving", "walking", "cycling"}


async def route(
    origin: tuple[float, float],
    destination: tuple[float, float],
    client: httpx.AsyncClient,
    profile: str = "driving",
) -> RouteResult | None:
    """Calculate a route between two points using OSRM.

    Args:
        origin: ``(lat, lon)`` tuple for the start point.
        destination: ``(lat, lon)`` tuple for the end point.
        client: Shared async HTTP client.
        profile: One of ``"driving"``, ``"walking"``, or ``"cycling"``.

    Returns:
        A :class:`RouteResult` with normalised route steps and the raw OSRM
        response in ``raw``.  Returns ``None`` on request failure.

    Raises:
        ValueError: If *profile* is not one of the supported values.
    """
    if profile not in _VALID_PROFILES:
        raise ValueError(
            f"Unsupported profile '{profile}'. Must be one of: "
            f"{', '.join(sorted(_VALID_PROFILES))}"
        )

    lat1, lon1 = origin
    lat2, lon2 = destination
    coordinates = f"{lon1},{lat1};{lon2},{lat2}"

    try:
        response = await client.get(
            f"{OSRM_API}/route/v1/{profile}/{coordinates}",
            params={"steps": "false", "overview": "full"},
            timeout=30,
        )
        if not response.is_success:
            return None
        data = response.json()
    except Exception:
        return None

    steps = [
        RouteStep(
            distance_m=r.get("distance", 0.0),
            duration_s=r.get("duration", 0.0),
            geometry=r.get("geometry", ""),
        )
        for r in data.get("routes", [])
    ]

    return RouteResult(
        profile=profile,
        origin=GeoPoint(lat=lat1, lon=lon1),
        destination=GeoPoint(lat=lat2, lon=lon2),
        routes=steps,
        raw=data,
    )
