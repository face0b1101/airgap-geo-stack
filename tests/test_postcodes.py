"""Tests for airgap_geo.postcodes."""

from __future__ import annotations

import re

import httpx

from airgap_geo.postcodes import lookup_outcode, lookup_postcode
from airgap_geo.settings import POSTCODES_URL

POSTCODE_RESULT = {
    "postcode": "SW1A 2AA",
    "latitude": 51.5034,
    "longitude": -0.1276,
    "admin_district": "Westminster",
    "admin_county": None,
    "admin_ward": "St James's",
    "parish": None,
    "region": "London",
    "country": "England",
    "primary_care_trust": "Westminster",
    "lsoa": "Westminster 018C",
    "msoa": "Westminster 018",
    "nuts": "Lambeth",
    "codes": {"admin_district": "E09000033"},
}

OUTCODE_RESULT = {
    "outcode": "SW1A",
    "latitude": 51.5028,
    "longitude": -0.1306,
    "admin_district": ["Westminster"],
    "parish": [],
    "admin_county": [],
    "admin_ward": ["St James's"],
    "country": ["England"],
}

_POSTCODE_URL = re.compile(rf"{re.escape(POSTCODES_URL)}/postcodes/.*")
_OUTCODE_URL = re.compile(rf"{re.escape(POSTCODES_URL)}/outcodes/.*")


class TestLookupPostcode:
    """Tests for lookup_postcode."""

    async def test_happy_path(self, httpx_mock):
        """Returns a PostcodeResult on a successful postcodes.io response."""
        httpx_mock.add_response(
            url=_POSTCODE_URL,
            json={"status": 200, "result": POSTCODE_RESULT},
            status_code=200,
        )
        async with httpx.AsyncClient() as client:
            result = await lookup_postcode("SW1A2AA", client)
        assert result is not None
        assert result.postcode == "SW1A 2AA"
        assert result.latitude == 51.5034
        assert result.admin_district == "Westminster"
        assert result.region == "London"

    async def test_non_200_returns_none(self, httpx_mock):
        """Returns None when the API responds with a non-200 status."""
        httpx_mock.add_response(
            url=_POSTCODE_URL,
            json={"status": 404, "error": "Postcode not found"},
            status_code=404,
        )
        async with httpx.AsyncClient() as client:
            result = await lookup_postcode("INVALID", client)
        assert result is None

    async def test_raw_field_preserved(self, httpx_mock):
        """The raw postcodes.io result dict is preserved in result.raw."""
        httpx_mock.add_response(
            url=_POSTCODE_URL,
            json={"status": 200, "result": POSTCODE_RESULT},
            status_code=200,
        )
        async with httpx.AsyncClient() as client:
            result = await lookup_postcode("SW1A2AA", client)
        assert result is not None
        assert result.raw["postcode"] == "SW1A 2AA"


class TestLookupOutcode:
    """Tests for lookup_outcode."""

    async def test_happy_path(self, httpx_mock):
        """Returns an OutcodeResult on a successful postcodes.io response."""
        httpx_mock.add_response(
            url=_OUTCODE_URL,
            json={"status": 200, "result": OUTCODE_RESULT},
            status_code=200,
        )
        async with httpx.AsyncClient() as client:
            result = await lookup_outcode("SW1A", client)
        assert result is not None
        assert result.outcode == "SW1A"
        assert result.latitude == 51.5028
        assert "Westminster" in result.admin_district

    async def test_non_200_returns_none(self, httpx_mock):
        """Returns None when the API responds with a non-200 status."""
        httpx_mock.add_response(
            url=_OUTCODE_URL,
            json={"status": 404, "error": "Outcode not found"},
            status_code=404,
        )
        async with httpx.AsyncClient() as client:
            result = await lookup_outcode("ZZZZZ", client)
        assert result is None

    async def test_raw_field_preserved(self, httpx_mock):
        """The raw postcodes.io result dict is preserved in result.raw."""
        httpx_mock.add_response(
            url=_OUTCODE_URL,
            json={"status": 200, "result": OUTCODE_RESULT},
            status_code=200,
        )
        async with httpx.AsyncClient() as client:
            result = await lookup_outcode("SW1A", client)
        assert result is not None
        assert result.raw["outcode"] == "SW1A"
