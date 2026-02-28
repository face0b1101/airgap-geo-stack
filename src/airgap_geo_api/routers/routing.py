"""Routing router: POST /route."""

from __future__ import annotations

from typing import Literal

import httpx
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from airgap_geo.models import GeoPoint, RouteResult
from airgap_geo.routing import route
from airgap_geo_api.cache import _route_cache, get_cached, set_cached

router = APIRouter(prefix="/route", tags=["routing"])

_ProfileLiteral = Literal["driving", "walking", "cycling"]


class RouteRequest(BaseModel):
    """Request body for the route endpoint."""

    origin: GeoPoint = Field(..., description="Start point as {lat, lon}")
    destination: GeoPoint = Field(..., description="End point as {lat, lon}")
    profile: _ProfileLiteral = Field(
        default="driving",
        description="Routing profile: driving, walking, or cycling",
    )


@router.post("", response_model=RouteResult, summary="Calculate a route")
async def calculate_route(request: Request, body: RouteRequest) -> RouteResult:
    """Calculate a route between two coordinate pairs.

    Returns a normalised :class:`RouteResult` including per-route distance,
    duration, and geometry.
    """
    cache_key = (
        f"{body.origin.lat},{body.origin.lon}"
        f"-{body.destination.lat},{body.destination.lon}"
        f"-{body.profile}"
    )
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
