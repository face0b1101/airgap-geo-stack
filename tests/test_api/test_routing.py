"""Tests for POST /route."""

from __future__ import annotations

import re

import httpx
from fastapi.testclient import TestClient

from airgap_geo.settings import OSRM_API

_OSRM_BASE = str(httpx.URL(OSRM_API))

OSRM_RESPONSE = {
    "code": "Ok",
    "routes": [
        {
            "distance": 338210.6,
            "duration": 12754.3,
            "geometry": "encodedpolyline...",
        }
    ],
    "waypoints": [],
}

_ORIGIN = {"lat": 51.5034, "lon": -0.1276}
_DEST = {"lat": 53.4808, "lon": -2.2426}

_OSRM_DRIVING_URL = re.compile(rf"{re.escape(_OSRM_BASE)}/route/v1/driving.*")
_OSRM_WALKING_URL = re.compile(rf"{re.escape(_OSRM_BASE)}/route/v1/walking.*")
_OSRM_CYCLING_URL = re.compile(rf"{re.escape(_OSRM_BASE)}/route/v1/cycling.*")


class TestRouteEndpoint:
    """Tests for POST /route."""

    def test_driving_route_returns_200(self, client: TestClient, httpx_mock):
        """A valid driving route request returns 200 with route steps."""
        httpx_mock.add_response(
            url=_OSRM_DRIVING_URL, json=OSRM_RESPONSE, status_code=200
        )
        response = client.post(
            "/route",
            json={"origin": _ORIGIN, "destination": _DEST, "profile": "driving"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["profile"] == "driving"
        assert len(data["routes"]) == 1
        assert data["routes"][0]["distance_m"] == 338210.6
        assert data["routes"][0]["duration_s"] == 12754.3

    def test_walking_route_returns_200(self, client: TestClient, httpx_mock):
        """A walking route request returns 200."""
        httpx_mock.add_response(
            url=_OSRM_WALKING_URL, json=OSRM_RESPONSE, status_code=200
        )
        response = client.post(
            "/route",
            json={"origin": _ORIGIN, "destination": _DEST, "profile": "walking"},
        )
        assert response.status_code == 200
        assert response.json()["profile"] == "walking"

    def test_cycling_route_returns_200(self, client: TestClient, httpx_mock):
        """A cycling route request returns 200."""
        httpx_mock.add_response(
            url=_OSRM_CYCLING_URL, json=OSRM_RESPONSE, status_code=200
        )
        response = client.post(
            "/route",
            json={"origin": _ORIGIN, "destination": _DEST, "profile": "cycling"},
        )
        assert response.status_code == 200
        assert response.json()["profile"] == "cycling"

    def test_invalid_profile_returns_422(self, client: TestClient):
        """An unrecognised profile fails FastAPI validation with 422."""
        response = client.post(
            "/route",
            json={"origin": _ORIGIN, "destination": _DEST, "profile": "flying"},
        )
        assert response.status_code == 422

    def test_osrm_failure_returns_502(self, client: TestClient, httpx_mock):
        """Returns 502 when OSRM responds with a non-200 status."""
        httpx_mock.add_response(
            url=_OSRM_DRIVING_URL, json={"code": "NoRoute"}, status_code=400
        )
        response = client.post(
            "/route",
            json={"origin": _ORIGIN, "destination": _DEST, "profile": "driving"},
        )
        assert response.status_code == 502

    def test_missing_body_returns_422(self, client: TestClient):
        """Returns 422 when the request body is absent."""
        response = client.post("/route")
        assert response.status_code == 422

    def test_origin_destination_in_response(self, client: TestClient, httpx_mock):
        """Origin and destination GeoPoints are included in the response."""
        httpx_mock.add_response(
            url=_OSRM_DRIVING_URL, json=OSRM_RESPONSE, status_code=200
        )
        response = client.post(
            "/route",
            json={"origin": _ORIGIN, "destination": _DEST},
        )
        data = response.json()
        assert data["origin"]["lat"] == 51.5034
        assert data["destination"]["lat"] == 53.4808

    def test_repeated_request_served_from_cache(self, client: TestClient, httpx_mock):
        """Identical route requests are served from cache after the first call."""
        httpx_mock.add_response(
            url=_OSRM_DRIVING_URL, json=OSRM_RESPONSE, status_code=200
        )
        body = {"origin": _ORIGIN, "destination": _DEST, "profile": "driving"}
        client.post("/route", json=body)
        client.post("/route", json=body)
        assert len(httpx_mock.get_requests()) == 1
