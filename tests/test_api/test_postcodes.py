"""Tests for GET /postcodes/{postcode} and GET /outcodes/{outcode}."""

from __future__ import annotations

import re

from fastapi.testclient import TestClient

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


class TestPostcodeEndpoint:
    """Tests for GET /postcodes/{postcode}."""

    def test_valid_postcode_returns_200(self, client: TestClient, httpx_mock):
        """A recognised postcode returns 200 with normalised data."""
        httpx_mock.add_response(
            url=_POSTCODE_URL,
            json={"status": 200, "result": POSTCODE_RESULT},
            status_code=200,
        )
        response = client.get("/postcodes/SW1A2AA")
        assert response.status_code == 200
        data = response.json()
        assert data["postcode"] == "SW1A 2AA"
        assert data["latitude"] == 51.5034
        assert data["admin_district"] == "Westminster"
        assert data["region"] == "London"

    def test_unknown_postcode_returns_404(self, client: TestClient, httpx_mock):
        """An unrecognised postcode returns 404."""
        httpx_mock.add_response(
            url=_POSTCODE_URL,
            json={"status": 404, "error": "Postcode not found"},
            status_code=404,
        )
        response = client.get("/postcodes/ZZ9Z9ZZ")
        assert response.status_code == 404

    def test_raw_field_present(self, client: TestClient, httpx_mock):
        """The raw postcodes.io result is included in the response."""
        httpx_mock.add_response(
            url=_POSTCODE_URL,
            json={"status": 200, "result": POSTCODE_RESULT},
            status_code=200,
        )
        response = client.get("/postcodes/SW1A2AA")
        data = response.json()
        assert data["raw"]["postcode"] == "SW1A 2AA"

    def test_repeated_lookup_served_from_cache(self, client: TestClient, httpx_mock):
        """A repeated postcode lookup is served from cache."""
        httpx_mock.add_response(
            url=_POSTCODE_URL,
            json={"status": 200, "result": POSTCODE_RESULT},
            status_code=200,
        )
        client.get("/postcodes/SW1A2AA")
        client.get("/postcodes/SW1A2AA")
        assert len(httpx_mock.get_requests()) == 1


class TestOutcodeEndpoint:
    """Tests for GET /outcodes/{outcode}."""

    def test_valid_outcode_returns_200(self, client: TestClient, httpx_mock):
        """A recognised outcode returns 200 with normalised data."""
        httpx_mock.add_response(
            url=_OUTCODE_URL,
            json={"status": 200, "result": OUTCODE_RESULT},
            status_code=200,
        )
        response = client.get("/outcodes/SW1A")
        assert response.status_code == 200
        data = response.json()
        assert data["outcode"] == "SW1A"
        assert data["latitude"] == 51.5028
        assert "Westminster" in data["admin_district"]

    def test_unknown_outcode_returns_404(self, client: TestClient, httpx_mock):
        """An unrecognised outcode returns 404."""
        httpx_mock.add_response(
            url=_OUTCODE_URL,
            json={"status": 404, "error": "Outcode not found"},
            status_code=404,
        )
        response = client.get("/outcodes/ZZZZZ")
        assert response.status_code == 404

    def test_repeated_lookup_served_from_cache(self, client: TestClient, httpx_mock):
        """A repeated outcode lookup is served from cache."""
        httpx_mock.add_response(
            url=_OUTCODE_URL,
            json={"status": 200, "result": OUTCODE_RESULT},
            status_code=200,
        )
        client.get("/outcodes/SW1A")
        client.get("/outcodes/SW1A")
        assert len(httpx_mock.get_requests()) == 1
