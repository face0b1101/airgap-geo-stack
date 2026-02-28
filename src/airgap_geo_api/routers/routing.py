"""Routing router: POST /route."""

from __future__ import annotations

import hashlib
import json
from typing import Annotated, Literal

import httpx
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from airgap_geo.geocoding import geocoder
from airgap_geo.models import Address, GeocodeResult, GeoPoint, RouteResult
from airgap_geo.routing import route
from airgap_geo_api.cache import _route_cache, get_cached, set_cached

router = APIRouter(prefix="/route", tags=["routing"])

_ProfileLiteral = Literal["driving", "walking", "cycling"]
_AnnotationLiteral = Literal[
    "duration", "distance", "speed", "nodes", "weight", "datasources"
]
_OverviewLiteral = Literal["full", "simplified", "false"]
_GeometriesLiteral = Literal["polyline", "polyline6", "geojson"]


class RouteRequest(BaseModel):
    """Request body for the route endpoint.

    ``origin``, ``destination``, and ``waypoints`` each accept either a
    ``{lat, lon}`` object **or** a text string (place name, postcode, or
    ``"lat,lon"``).  Text values are geocoded automatically via Nominatim
    before routing.
    """

    origin: str | GeoPoint = Field(
        ...,
        description=(
            "Start location — a {lat, lon} object, a place name, "
            "a postcode, or a 'lat,lon' string"
        ),
    )
    destination: str | GeoPoint = Field(
        ...,
        description=(
            "End location — a {lat, lon} object, a place name, "
            "a postcode, or a 'lat,lon' string"
        ),
    )
    waypoints: list[str | GeoPoint] | None = Field(
        default=None,
        description=(
            "Optional intermediate waypoints in travel order. "
            "Each may be a {lat, lon} object or a text string."
        ),
    )
    profile: _ProfileLiteral = Field(
        default="driving",
        description="Routing profile: driving, walking, or cycling",
    )
    steps: bool = Field(
        default=False,
        description="Include turn-by-turn manoeuvre steps per leg",
    )
    alternatives: Annotated[bool | int, Field(ge=0)] = Field(
        default=False,
        description="Request alternative routes. True for any alternatives, or an integer count",
    )
    annotations: list[_AnnotationLiteral] | None = Field(
        default=None,
        description="Per-segment annotation keys: duration, distance, speed, nodes, weight, datasources",
    )
    overview: _OverviewLiteral = Field(
        default="full",
        description="Geometry detail level: full, simplified, or false",
    )
    geometries: _GeometriesLiteral = Field(
        default="polyline",
        description="Route geometry encoding: polyline, polyline6, or geojson",
    )
    continue_straight: bool | None = Field(
        default=None,
        description="Bias against U-turns at intermediate waypoints",
    )
    exclude: list[str] | None = Field(
        default=None,
        description="Road classes to avoid, e.g. ['motorway', 'toll', 'ferry']",
    )


async def _resolve_location(
    location: str | GeoPoint, label: str, client: httpx.AsyncClient
) -> tuple[GeoPoint, Address | None]:
    """Resolve a location field to a GeoPoint and optional Address.

    If *location* is already a :class:`GeoPoint`, return it directly with no
    address.  If it is a string, geocode it via :func:`geocoder` and extract
    both the coordinate and the address.

    Raises:
        ValueError: If geocoding fails for a text location.
    """
    if isinstance(location, GeoPoint):
        return location, None

    result: GeocodeResult | None = await geocoder(location, client)
    if result is None:
        raise ValueError(f"Could not geocode {label}: '{location}'")
    return result.geo, result.address


def _resolved_cache_key(
    origin: GeoPoint,
    destination: GeoPoint,
    waypoints: list[GeoPoint],
    body: RouteRequest,
) -> str:
    """Derive a stable cache key from resolved coordinates + routing options.

    The key is computed from the *resolved* coordinates so that text and
    coordinate inputs that resolve to the same point share a cache entry.
    """
    payload = {
        "origin": {"lat": origin.lat, "lon": origin.lon},
        "destination": {"lat": destination.lat, "lon": destination.lon},
        "waypoints": [{"lat": wp.lat, "lon": wp.lon} for wp in waypoints],
        "profile": body.profile,
        "steps": body.steps,
        "alternatives": body.alternatives,
        "annotations": list(body.annotations) if body.annotations else None,
        "overview": body.overview,
        "geometries": body.geometries,
        "continue_straight": body.continue_straight,
        "exclude": list(body.exclude) if body.exclude else None,
    }
    serialised = json.dumps(payload, sort_keys=True)
    return hashlib.sha256(serialised.encode()).hexdigest()


@router.post("", response_model=RouteResult, summary="Calculate a route")
async def calculate_route(request: Request, body: RouteRequest) -> RouteResult:
    """Calculate a route between two or more locations.

    Origin, destination, and waypoints can be supplied as ``{lat, lon}``
    coordinate objects **or** as text strings (place names, postcodes, or
    ``"lat,lon"`` strings).  Text values are geocoded automatically.

    When geocoding is used, the response includes ``origin_address``,
    ``destination_address``, and ``waypoint_addresses`` with the resolved
    address metadata.
    """
    client: httpx.AsyncClient = request.app.state.http_client

    try:
        origin_point, origin_addr = await _resolve_location(
            body.origin, "origin", client
        )
        dest_point, dest_addr = await _resolve_location(
            body.destination, "destination", client
        )

        wp_points: list[GeoPoint] = []
        wp_addrs: list[Address] = []
        for idx, wp in enumerate(body.waypoints or []):
            pt, addr = await _resolve_location(wp, f"waypoint[{idx}]", client)
            wp_points.append(pt)
            if addr is not None:
                wp_addrs.append(addr)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    cache_key = _resolved_cache_key(origin_point, dest_point, wp_points, body)
    cached = await get_cached(_route_cache, cache_key)
    if cached is not None:
        return cached

    try:
        result = await route(
            origin=(origin_point.lat, origin_point.lon),
            destination=(dest_point.lat, dest_point.lon),
            client=client,
            profile=body.profile,
            waypoints=[(wp.lat, wp.lon) for wp in wp_points] if wp_points else None,
            steps=body.steps,
            alternatives=body.alternatives,
            annotations=list(body.annotations) if body.annotations else None,
            overview=body.overview,
            geometries=body.geometries,
            continue_straight=body.continue_straight,
            exclude=list(body.exclude) if body.exclude else None,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    if result is None:
        raise HTTPException(
            status_code=502,
            detail="Routing service returned no result. Check OSRM is running.",
        )

    result.origin_address = origin_addr
    result.destination_address = dest_addr
    result.waypoint_addresses = wp_addrs

    await set_cached(_route_cache, cache_key, result)
    return result
