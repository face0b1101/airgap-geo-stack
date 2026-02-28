"""Tests for GET /geocode."""

from __future__ import annotations

import re

import pytest
from fastapi.testclient import TestClient

from airgap_geo.settings import NOMINATIM_URL, PHOTON_API

PHOTON_FEATURE = {
    "type": "Feature",
    "geometry": {"type": "Point", "coordinates": [-0.1276, 51.5034]},
    "properties": {
        "name": "10 Downing Street",
        "city": "London",
        "country": "United Kingdom",
        "countrycode": "GB",
        "street": "Downing Street",
        "postcode": "SW1A 2AA",
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


class TestGeocodeEndpoint:
    """Tests for GET /geocode."""

    def test_coordinate_query_returns_200(self, client: TestClient, httpx_mock):
        """A lat,lon string resolves via Photon and returns 200."""
        httpx_mock.add_response(
            url=_PHOTON_REVERSE_URL, json=PHOTON_RESPONSE, status_code=200
        )
        response = client.get("/geocode", params={"q": "51.5034,-0.1276"})
        assert response.status_code == 200
        data = response.json()
        assert data["geo"]["lat"] == pytest.approx(51.5034, abs=1e-4)
        assert data["geo"]["lon"] == pytest.approx(-0.1276, abs=1e-4)
        assert data["address"]["city"] == "London"

    def test_place_name_query_returns_200(self, client: TestClient, httpx_mock):
        """A free-text place name hits Nominatim then Photon."""
        httpx_mock.add_response(
            url=_NOMINATIM_SEARCH_URL, json=NOMINATIM_RESULT, status_code=200
        )
        httpx_mock.add_response(
            url=_PHOTON_REVERSE_URL, json=PHOTON_RESPONSE, status_code=200
        )
        response = client.get("/geocode", params={"q": "10 Downing Street London"})
        assert response.status_code == 200
        data = response.json()
        assert data["address"]["name"] == "10 Downing Street"
        assert data["address"]["postcode"] == "SW1A 2AA"

    def test_not_found_returns_404(self, client: TestClient, httpx_mock):
        """Returns 404 when Nominatim finds nothing."""
        httpx_mock.add_response(url=_NOMINATIM_SEARCH_URL, json=[], status_code=200)
        response = client.get("/geocode", params={"q": "zzz-does-not-exist"})
        assert response.status_code == 404

    def test_missing_q_returns_422(self, client: TestClient):
        """Returns 422 when the required q parameter is omitted."""
        response = client.get("/geocode")
        assert response.status_code == 422

    def test_raw_field_present(self, client: TestClient, httpx_mock):
        """The raw Photon feature is included in the response."""
        httpx_mock.add_response(
            url=_PHOTON_REVERSE_URL, json=PHOTON_RESPONSE, status_code=200
        )
        response = client.get("/geocode", params={"q": "51.5034,-0.1276"})
        data = response.json()
        assert data["raw"]["type"] == "Feature"

    def test_repeated_query_served_from_cache(self, client: TestClient, httpx_mock):
        """A repeated identical query is served from cache (only one upstream call)."""
        httpx_mock.add_response(
            url=_PHOTON_REVERSE_URL, json=PHOTON_RESPONSE, status_code=200
        )
        client.get("/geocode", params={"q": "51.5034,-0.1276"})
        response = client.get("/geocode", params={"q": "51.5034,-0.1276"})
        assert response.status_code == 200
        assert len(httpx_mock.get_requests()) == 1
