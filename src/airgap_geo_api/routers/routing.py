"""Routing router: POST /route."""

from __future__ import annotations

import hashlib
import json
from typing import Annotated, Literal

import httpx
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from airgap_geo.models import GeoPoint, RouteResult
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
    """Request body for the route endpoint."""

    origin: GeoPoint = Field(..., description="Start point as {lat, lon}")
    destination: GeoPoint = Field(..., description="End point as {lat, lon}")
    waypoints: list[GeoPoint] | None = Field(
        default=None,
        description="Optional intermediate waypoints in travel order",
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


def _cache_key(body: RouteRequest) -> str:
    """Derive a stable cache key from the full request body."""
    payload = body.model_dump(mode="json")
    serialised = json.dumps(payload, sort_keys=True)
    return hashlib.sha256(serialised.encode()).hexdigest()


@router.post("", response_model=RouteResult, summary="Calculate a route")
async def calculate_route(request: Request, body: RouteRequest) -> RouteResult:
    """Calculate a route between two or more coordinate pairs.

    Returns a normalised :class:`RouteResult` including per-route distance,
    duration, geometry, and optional per-leg steps and annotations.

    Intermediate **waypoints** can be provided to route through multiple points
    in order. Optional parameters expose the full OSRM route feature set:
    turn-by-turn steps, alternative routes, per-segment annotations, geometry
    format, and road-class exclusions.
    """
    cache_key = _cache_key(body)
    cached = await get_cached(_route_cache, cache_key)
    if cached is not None:
        return cached

    client: httpx.AsyncClient = request.app.state.http_client
    try:
        result = await route(
            origin=(body.origin.lat, body.origin.lon),
            destination=(body.destination.lat, body.destination.lon),
            client=client,
            profile=body.profile,
            waypoints=[(wp.lat, wp.lon) for wp in body.waypoints]
            if body.waypoints
            else None,
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

    await set_cached(_route_cache, cache_key, result)
    return result
