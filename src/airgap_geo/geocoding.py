"""Geocoding helpers backed by Photon and Nominatim."""

from __future__ import annotations

import httpx

from airgap_geo.models import Address, GeocodeResult, GeoPoint
from airgap_geo.settings import NOMINATIM_URL, PHOTON_API

_COORD_BOUNDS = {
    "lat": (-90.0, 90.0),
    "lon": (-180.0, 180.0),
}

# Mapping from Photon property keys to Address field names.
_PHOTON_FIELD_MAP: dict[str, str] = {
    "name": "name",
    "housenumber": "house_number",
    "street": "street",
    "postcode": "postcode",
    "city": "city",
    "state": "state",
    "country": "country",
    "countrycode": "country_code",
}


def _address_from_photon(properties: dict) -> Address:
    """Extract a normalised Address from a Photon feature properties dict."""
    kwargs = {
        field: properties.get(photon_key)
        for photon_key, field in _PHOTON_FIELD_MAP.items()
    }
    return Address(**kwargs)


async def photon_reverse_geocode(
    lat: float, lon: float, client: httpx.AsyncClient
) -> dict:
    """Reverse geocode a coordinate pair using Photon.

    Args:
        lat: Latitude in decimal degrees.
        lon: Longitude in decimal degrees.
        client: Shared async HTTP client.

    Returns:
        The first feature from the Photon response, or an empty dict on failure.
    """
    try:
        response = await client.get(
            f"{PHOTON_API}/reverse",
            params={"lat": lat, "lon": lon},
            timeout=10,
        )
        if not response.is_success:
            return {}
        data = response.json()
        features = data.get("features", [])
        return features[0] if features else {}
    except Exception:
        return {}


async def nominatim_geocoder(location: str, client: httpx.AsyncClient) -> dict:
    """Forward geocode a place name or postcode using Nominatim.

    Args:
        location: Free-text place name or postcode string.
        client: Shared async HTTP client.

    Returns:
        The first Nominatim result dict, or an empty dict on failure / no results.
    """
    try:
        response = await client.get(
            f"{NOMINATIM_URL}/search",
            params={"q": location, "format": "jsonv2", "limit": 1},
            timeout=10,
        )
        if not response.is_success:
            return {}
        results = response.json()
        return results[0] if results else {}
    except Exception:
        return {}


def _is_valid_coord(value: float, kind: str) -> bool:
    lo, hi = _COORD_BOUNDS[kind]
    return lo <= value <= hi


async def geocoder(location: str, client: httpx.AsyncClient) -> GeocodeResult | None:
    """Geocode a location string to a normalised GeocodeResult.

    Accepts either a ``"lat,lon"`` coordinate string or a free-text place name /
    postcode. Coordinate strings are validated for plausible bounds; invalid
    coordinates are treated as place-name queries and forwarded to Nominatim.

    Args:
        location: Either ``"lat,lon"`` or a free-text query string.
        client: Shared async HTTP client.

    Returns:
        A :class:`GeocodeResult` with a populated ``geo`` and ``address``, plus
        the raw Photon feature in ``raw``.  Returns ``None`` if geocoding fails.
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
        nominatim_result = await nominatim_geocoder(location, client)
        if not nominatim_result:
            return None
        try:
            lat = float(nominatim_result["lat"])
            lon = float(nominatim_result["lon"])
        except (KeyError, ValueError):
            return None

    raw_feature = await photon_reverse_geocode(lat, lon, client)
    address = _address_from_photon(raw_feature.get("properties", {}))

    return GeocodeResult(
        geo=GeoPoint(lat=lat, lon=lon),
        address=address,
        raw=raw_feature,
    )
