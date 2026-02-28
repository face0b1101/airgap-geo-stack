"""UK postcode and outcode lookup helpers backed by postcodes.io."""

from __future__ import annotations

import requests

from airgap_geocoding.settings import POSTCODES_URL


def lookup_postcode(postcode: str) -> dict:
    """Look up a full UK postcode via postcodes.io.

    Args:
        postcode: A full UK postcode, e.g. ``"SW1A 2AA"``.

    Returns:
        The ``result`` value from the postcodes.io response, or an empty dict
        on failure.
    """
    try:
        response = requests.get(
            f"{POSTCODES_URL}/postcodes/{postcode}",
            timeout=10,
        )
        if not response.ok:
            return {}
        return response.json().get("result", {}) or {}
    except Exception:
        return {}


def lookup_outcode(outcode: str) -> dict:
    """Look up a UK outcode (district) via postcodes.io.

    Args:
        outcode: A UK outcode, e.g. ``"SW1A"``.

    Returns:
        The ``result`` value from the postcodes.io response, or an empty dict
        on failure.
    """
    try:
        response = requests.get(
            f"{POSTCODES_URL}/outcodes/{outcode}",
            timeout=10,
        )
        if not response.ok:
            return {}
        return response.json().get("result", {}) or {}
    except Exception:
        return {}
