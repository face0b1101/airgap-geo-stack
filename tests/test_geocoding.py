"""Tests for airgap_geo.geocoding."""

from __future__ import annotations

import re

import httpx
import pytest

from airgap_geo.geocoding import (
    geocoder,
    nominatim_geocoder,
    photon_reverse_geocode,
)
from airgap_geo.settings import NOMINATIM_URL, PHOTON_API

PHOTON_FEATURE = {
    "type": "Feature",
    "geometry": {"type": "Point", "coordinates": [-0.1276, 51.5034]},
    "properties": {
        "name": "10 Downing Street",
        "city": "London",
        "country": "United Kingdom",
        "countrycode": "GB",
    },
}

PHOTON_RESPONSE = {"type": "FeatureCollection", "features": [PHOTON_FEATURE]}

NOMINATIM_RESULT = [
    {
        "place_id": 1,
        "lat": "51.5034",
        "lon": "-0.1276",
        "display_name": "10 Downing Street, London",
    }
]

_PHOTON_REVERSE_URL = re.compile(rf"{re.escape(PHOTON_API)}/reverse.*")
_NOMINATIM_SEARCH_URL = re.compile(rf"{re.escape(NOMINATIM_URL)}/search.*")


class TestPhotonReverseGeocode:
    """Tests for photon_reverse_geocode."""

    async def test_happy_path(self, httpx_mock):
        """Returns the first feature on a successful response."""
        httpx_mock.add_response(
            url=_PHOTON_REVERSE_URL, json=PHOTON_RESPONSE, status_code=200
        )
        async with httpx.AsyncClient() as client:
            result = await photon_reverse_geocode(51.5034, -0.1276, client)
        assert result == PHOTON_FEATURE

    async def test_non_200_returns_empty(self, httpx_mock):
        """Returns empty dict when the API responds with a non-200 status."""
        httpx_mock.add_response(
            url=_PHOTON_REVERSE_URL, json={"error": "not found"}, status_code=404
        )
        async with httpx.AsyncClient() as client:
            result = await photon_reverse_geocode(51.5034, -0.1276, client)
        assert result == {}

    async def test_empty_features_returns_empty(self, httpx_mock):
        """Returns empty dict when the features list is empty."""
        httpx_mock.add_response(
            url=_PHOTON_REVERSE_URL,
            json={"type": "FeatureCollection", "features": []},
            status_code=200,
        )
        async with httpx.AsyncClient() as client:
            result = await photon_reverse_geocode(51.5034, -0.1276, client)
        assert result == {}


class TestNominatimGeocoder:
    """Tests for nominatim_geocoder."""

    async def test_happy_path(self, httpx_mock):
        """Returns the first result on a successful response."""
        httpx_mock.add_response(
            url=_NOMINATIM_SEARCH_URL, json=NOMINATIM_RESULT, status_code=200
        )
        async with httpx.AsyncClient() as client:
            result = await nominatim_geocoder("10 Downing Street London", client)
        assert result["lat"] == "51.5034"
        assert result["lon"] == "-0.1276"

    async def test_non_200_returns_empty(self, httpx_mock):
        """Returns empty dict when the API responds with a non-200 status."""
        httpx_mock.add_response(
            url=_NOMINATIM_SEARCH_URL, json={"error": "server error"}, status_code=500
        )
        async with httpx.AsyncClient() as client:
            result = await nominatim_geocoder("Nowhere", client)
        assert result == {}

    async def test_empty_results_returns_empty(self, httpx_mock):
        """Returns empty dict when no results are returned."""
        httpx_mock.add_response(url=_NOMINATIM_SEARCH_URL, json=[], status_code=200)
        async with httpx.AsyncClient() as client:
            result = await nominatim_geocoder("zzz-does-not-exist", client)
        assert result == {}


class TestGeocoder:
    """Tests for geocoder."""

    async def test_coordinate_string_input(self, httpx_mock):
        """Parses a lat,lon string and reverse geocodes without hitting Nominatim."""
        httpx_mock.add_response(
            url=_PHOTON_REVERSE_URL, json=PHOTON_RESPONSE, status_code=200
        )
        async with httpx.AsyncClient() as client:
            result = await geocoder("51.5034,-0.1276", client)
        assert result is not None
        assert result.geo.lat == pytest.approx(51.5034, abs=1e-4)
        assert result.geo.lon == pytest.approx(-0.1276, abs=1e-4)
        assert result.address is not None
        assert result.address.city == "London"

    async def test_place_name_input(self, httpx_mock):
        """Geocodes a place name via Nominatim then enriches via Photon."""
        httpx_mock.add_response(
            url=_NOMINATIM_SEARCH_URL, json=NOMINATIM_RESULT, status_code=200
        )
        httpx_mock.add_response(
            url=_PHOTON_REVERSE_URL, json=PHOTON_RESPONSE, status_code=200
        )
        async with httpx.AsyncClient() as client:
            result = await geocoder("10 Downing Street London", client)
        assert result is not None
        assert result.geo.lat == pytest.approx(51.5034, abs=1e-4)
        assert result.geo.lon == pytest.approx(-0.1276, abs=1e-4)
        assert result.address is not None
        assert result.address.name == "10 Downing Street"

    async def test_invalid_coords_fall_through_to_nominatim(self, httpx_mock):
        """Out-of-range coordinates are treated as a place-name query."""
        httpx_mock.add_response(
            url=_NOMINATIM_SEARCH_URL, json=NOMINATIM_RESULT, status_code=200
        )
        httpx_mock.add_response(
            url=_PHOTON_REVERSE_URL, json=PHOTON_RESPONSE, status_code=200
        )
        async with httpx.AsyncClient() as client:
            result = await geocoder("999,-0.1276", client)
        assert result is not None
        assert result.geo is not None

    async def test_empty_nominatim_result_returns_none(self, httpx_mock):
        """Returns None when Nominatim finds no matching location."""
        httpx_mock.add_response(url=_NOMINATIM_SEARCH_URL, json=[], status_code=200)
        async with httpx.AsyncClient() as client:
            result = await geocoder("zzz-does-not-exist", client)
        assert result is None

    async def test_raw_field_preserved(self, httpx_mock):
        """The raw Photon feature is preserved in result.raw."""
        httpx_mock.add_response(
            url=_PHOTON_REVERSE_URL, json=PHOTON_RESPONSE, status_code=200
        )
        async with httpx.AsyncClient() as client:
            result = await geocoder("51.5034,-0.1276", client)
        assert result is not None
        assert result.raw == PHOTON_FEATURE
