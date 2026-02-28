"""Geocoding helpers backed by Photon and Nominatim."""

from __future__ import annotations

import requests

from airgap_geocoding.settings import NOMINATIM_URL, PHOTON_API

_COORD_BOUNDS = {
    "lat": (-90.0, 90.0),
    "lon": (-180.0, 180.0),
}


def photon_reverse_geocode(lat: float, lon: float) -> dict:
    """Reverse geocode a coordinate pair using Photon.

    Args:
        lat: Latitude in decimal degrees.
        lon: Longitude in decimal degrees.

    Returns:
        The first feature from the Photon response, or an empty dict on failure.
    """
    try:
        response = requests.get(
            f"{PHOTON_API}/reverse",
            params={"lat": lat, "lon": lon},
            timeout=10,
        )
        if not response.ok:
            return {}
        data = response.json()
        features = data.get("features", [])
        return features[0] if features else {}
    except Exception:
        return {}


def nominatim_geocoder(location: str) -> dict:
    """Forward geocode a place name or postcode using Nominatim.

    Args:
        location: Free-text place name or postcode string.

    Returns:
        The first Nominatim result dict, or an empty dict on failure / no results.
    """
    try:
        response = requests.get(
            f"{NOMINATIM_URL}/search",
            params={"q": location, "format": "jsonv2", "limit": 1},
            timeout=10,
        )
        if not response.ok:
            return {}
        results = response.json()
        return results[0] if results else {}
    except Exception:
        return {}


def _is_valid_coord(value: float, kind: str) -> bool:
    lo, hi = _COORD_BOUNDS[kind]
    return lo <= value <= hi


def geocoder(location: str) -> dict:
    """Geocode a location string to a GeoJSON feature dict.

    Accepts either a ``"lat,lon"`` coordinate string or a free-text place name /
    postcode. Coordinate strings are validated for plausible bounds; invalid
    coordinates are treated as place-name queries and forwarded to Nominatim.

    The result is always enriched with a top-level ``geo`` key containing
    ``{"lat": float, "lon": float}``.

    Args:
        location: Either ``"lat,lon"`` or a free-text query string.

    Returns:
        A GeoJSON feature dict with an additional ``geo`` key, or an empty dict
        if geocoding fails.
    """
    lat: float | None = None
    lon: float | None = None

    parts = location.split(",", 1)
    if len(parts) == 2:
        try:
            candidate_lat = float(parts[0].strip())
            candidate_lon = float(parts[1].strip())
            if _is_valid_coord(candidate_lat, "lat") and _is_valid_coord(
                candidate_lon, "lon"
            ):
                lat, lon = candidate_lat, candidate_lon
        except ValueError:
            pass

    if lat is None or lon is None:
        nominatim_result = nominatim_geocoder(location)
        if not nominatim_result:
            return {}
        try:
            lat = float(nominatim_result["lat"])
            lon = float(nominatim_result["lon"])
        except (KeyError, ValueError):
            return {}

    feature = photon_reverse_geocode(lat, lon)
    feature["geo"] = {"lat": lat, "lon": lon}
    return feature
