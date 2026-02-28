"""Routing helpers backed by OSRM via HAProxy."""

from __future__ import annotations

import requests

from airgap_geocoding.settings import OSRM_API

_VALID_PROFILES = {"driving", "walking", "cycling"}


def route(
    origin: tuple[float, float],
    destination: tuple[float, float],
    profile: str = "driving",
) -> dict:
    """Calculate a route between two points using OSRM.

    Args:
        origin: ``(lat, lon)`` tuple for the start point.
        destination: ``(lat, lon)`` tuple for the end point.
        profile: One of ``"driving"``, ``"walking"``, or ``"cycling"``.

    Returns:
        The raw OSRM JSON response dict, or an empty dict on request failure.

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
        response = requests.get(
            f"{OSRM_API}/route/v1/{profile}/{coordinates}",
            params={"steps": "false", "overview": "full"},
            timeout=30,
        )
        if not response.ok:
            return {}
        return response.json()
    except Exception:
        return {}
