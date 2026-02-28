"""Postcodes router: GET /postcodes/{postcode} and GET /outcodes/{outcode}."""

from __future__ import annotations

import httpx
from fastapi import APIRouter, HTTPException, Path, Request

from airgap_geo.models import OutcodeResult, PostcodeResult
from airgap_geo.postcodes import lookup_outcode, lookup_postcode
from airgap_geo_api.cache import _postcode_cache, get_cached, set_cached

router = APIRouter(tags=["postcodes"])


@router.get(
    "/postcodes/{postcode}",
    response_model=PostcodeResult,
    summary="Look up a UK postcode",
)
async def get_postcode(
    request: Request,
    postcode: str = Path(..., description="Full UK postcode, e.g. SW1A 2AA"),
) -> PostcodeResult:
    """Return normalised data for a full UK postcode."""
    cache_key = f"pc:{postcode.upper().replace(' ', '')}"
    cached = await get_cached(_postcode_cache, cache_key)
    if cached is not None:
        return cached

    client: httpx.AsyncClient = request.app.state.http_client
    result = await lookup_postcode(postcode, client)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Postcode '{postcode}' not found")

    await set_cached(_postcode_cache, cache_key, result)
    return result


@router.get(
    "/outcodes/{outcode}",
    response_model=OutcodeResult,
    summary="Look up a UK outcode",
)
async def get_outcode(
    request: Request,
    outcode: str = Path(..., description="UK outcode (district), e.g. SW1A"),
) -> OutcodeResult:
    """Return normalised data for a UK outcode (postcode district)."""
    cache_key = f"oc:{outcode.upper()}"
    cached = await get_cached(_postcode_cache, cache_key)
    if cached is not None:
        return cached

    client: httpx.AsyncClient = request.app.state.http_client
    result = await lookup_outcode(outcode, client)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Outcode '{outcode}' not found")

    await set_cached(_postcode_cache, cache_key, result)
    return result
