"""Geocoding router: GET /geocode."""

from __future__ import annotations

import httpx
from fastapi import APIRouter, HTTPException, Query, Request

from airgap_geo.geocoding import geocoder
from airgap_geo.models import GeocodeResult
from airgap_geo_api.cache import _geocode_cache, get_cached, set_cached

router = APIRouter(prefix="/geocode", tags=["geocoding"])


@router.get("", response_model=GeocodeResult, summary="Geocode a location")
async def geocode(
    request: Request,
    q: str = Query(..., description="Place name, postcode, or 'lat,lon' string"),
) -> GeocodeResult:
    """Geocode a free-text query or coordinate string.

    Accepts either a ``lat,lon`` coordinate pair or a free-text place name /
    postcode.  Returns a normalised :class:`GeocodeResult`.
    """
    cache_key = q.strip().lower()
    cached = await get_cached(_geocode_cache, cache_key)
    if cached is not None:
        return cached

    client: httpx.AsyncClient = request.app.state.http_client
    result = await geocoder(q, client)
    if result is None:
        raise HTTPException(status_code=404, detail=f"No geocoding result for '{q}'")

    await set_cached(_geocode_cache, cache_key, result)
    return result
