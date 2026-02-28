"""UK postcode and outcode lookup helpers backed by postcodes.io."""

from __future__ import annotations

import httpx

from airgap_geo.models import OutcodeResult, PostcodeResult
from airgap_geo.settings import POSTCODES_URL


async def lookup_postcode(
    postcode: str, client: httpx.AsyncClient
) -> PostcodeResult | None:
    """Look up a full UK postcode via postcodes.io.

    Args:
        postcode: A full UK postcode, e.g. ``"SW1A 2AA"``.
        client: Shared async HTTP client.

    Returns:
        A :class:`PostcodeResult` with normalised fields and the raw
        postcodes.io result in ``raw``.  Returns ``None`` on failure.
    """
    try:
        response = await client.get(
            f"{POSTCODES_URL}/postcodes/{postcode}",
            timeout=10,
        )
        if not response.is_success:
            return None
        data = response.json().get("result") or {}
    except Exception:
        return None

    if not data:
        return None

    return PostcodeResult(
        postcode=data.get("postcode", postcode),
        latitude=data.get("latitude"),
        longitude=data.get("longitude"),
        admin_district=data.get("admin_district"),
        admin_county=data.get("admin_county"),
        admin_ward=data.get("admin_ward"),
        parish=data.get("parish"),
        region=data.get("region"),
        country=data.get("country"),
        primary_care_trust=data.get("primary_care_trust"),
        lsoa=data.get("lsoa"),
        msoa=data.get("msoa"),
        nuts=data.get("nuts"),
        codes=data.get("codes", {}),
        raw=data,
    )


async def lookup_outcode(
    outcode: str, client: httpx.AsyncClient
) -> OutcodeResult | None:
    """Look up a UK outcode (district) via postcodes.io.

    Args:
        outcode: A UK outcode, e.g. ``"SW1A"``.
        client: Shared async HTTP client.

    Returns:
        A :class:`OutcodeResult` with normalised fields and the raw
        postcodes.io result in ``raw``.  Returns ``None`` on failure.
    """
    try:
        response = await client.get(
            f"{POSTCODES_URL}/outcodes/{outcode}",
            timeout=10,
        )
        if not response.is_success:
            return None
        data = response.json().get("result") or {}
    except Exception:
        return None

    if not data:
        return None

    return OutcodeResult(
        outcode=data.get("outcode", outcode),
        latitude=data.get("latitude"),
        longitude=data.get("longitude"),
        admin_district=data.get("admin_district") or [],
        parish=data.get("parish") or [],
        admin_county=data.get("admin_county") or [],
        admin_ward=data.get("admin_ward") or [],
        country=data.get("country") or [],
        raw=data,
    )
