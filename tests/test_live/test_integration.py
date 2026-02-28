"""Live integration tests against running Docker backend services.

Run with::

    make test-live

Requires all four services to be up (``make up``).
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from airgap_geo.geocoding import geocoder, nominatim_geocoder, photon_reverse_geocode
from airgap_geo.postcodes import lookup_outcode, lookup_postcode
from airgap_geo.routing import route

from .conftest import live, skip_unless_live

pytestmark = [live, skip_unless_live]

LONDON_LAT, LONDON_LON = 51.5034, -0.1276
MANCHESTER_LAT, MANCHESTER_LON = 53.4808, -2.2426
POSTCODE = "SW1A 2AA"
OUTCODE = "SW1A"


# ============================================================================
# Service-module tests (airgap_geo.*)
# ============================================================================


class TestGeocodingService:
    """Live tests for the geocoding service module."""

    async def test_reverse_geocode_london(self, http_client):
        """Photon reverse-geocodes London coordinates."""
        result = await photon_reverse_geocode(LONDON_LAT, LONDON_LON, http_client)
        assert result, "Expected a non-empty Photon feature"
        assert "properties" in result
        assert result["geometry"]["type"] == "Point"

    async def test_nominatim_forward_geocode(self, http_client):
        """Nominatim resolves a well-known address."""
        result = await nominatim_geocoder("10 Downing Street London", http_client)
        assert result, "Expected a Nominatim result"
        assert float(result["lat"]) == pytest.approx(LONDON_LAT, abs=0.05)

    async def test_geocoder_with_coordinates(self, http_client):
        """geocoder() resolves a lat,lon string."""
        result = await geocoder(f"{LONDON_LAT},{LONDON_LON}", http_client)
        assert result is not None
        assert result.geo.lat == pytest.approx(LONDON_LAT, abs=0.01)
        assert result.address is not None

    async def test_geocoder_with_place_name(self, http_client):
        """geocoder() resolves a free-text place name."""
        result = await geocoder("Manchester", http_client)
        assert result is not None
        assert result.geo.lat == pytest.approx(MANCHESTER_LAT, abs=0.1)


class TestRoutingService:
    """Live tests for the routing service module."""

    async def test_driving_route(self, http_client):
        """London-to-Manchester driving route returns a sensible distance."""
        result = await route(
            (LONDON_LAT, LONDON_LON),
            (MANCHESTER_LAT, MANCHESTER_LON),
            http_client,
            profile="driving",
        )
        assert result is not None
        assert result.profile == "driving"
        assert len(result.routes) >= 1
        assert result.routes[0].distance_m > 200_000

    async def test_walking_route(self, http_client):
        """A short walking route succeeds."""
        result = await route(
            (LONDON_LAT, LONDON_LON),
            (LONDON_LAT + 0.01, LONDON_LON + 0.01),
            http_client,
            profile="walking",
        )
        assert result is not None
        assert result.profile == "walking"

    async def test_cycling_route(self, http_client):
        """A short cycling route succeeds."""
        result = await route(
            (LONDON_LAT, LONDON_LON),
            (LONDON_LAT + 0.01, LONDON_LON + 0.01),
            http_client,
            profile="cycling",
        )
        assert result is not None
        assert result.profile == "cycling"

    async def test_route_with_waypoint(self, http_client):
        """A route via Cambridge produces at least two legs."""
        result = await route(
            (LONDON_LAT, LONDON_LON),
            (MANCHESTER_LAT, MANCHESTER_LON),
            http_client,
            waypoints=[(52.2053, -0.1218)],
        )
        assert result is not None
        assert len(result.waypoints) == 1
        assert len(result.routes[0].legs) >= 2

    async def test_route_with_steps(self, http_client):
        """Turn-by-turn steps are populated when requested."""
        result = await route(
            (LONDON_LAT, LONDON_LON),
            (MANCHESTER_LAT, MANCHESTER_LON),
            http_client,
            steps=True,
        )
        assert result is not None
        assert len(result.routes[0].legs[0].steps) > 0

    async def test_route_with_alternatives(self, http_client):
        """Requesting alternatives returns at least one route."""
        result = await route(
            (LONDON_LAT, LONDON_LON),
            (MANCHESTER_LAT, MANCHESTER_LON),
            http_client,
            alternatives=True,
        )
        assert result is not None
        assert len(result.routes) >= 1


class TestPostcodesService:
    """Live tests for the postcodes service module."""

    async def test_lookup_postcode(self, http_client):
        """A known UK postcode resolves correctly."""
        result = await lookup_postcode(POSTCODE, http_client)
        assert result is not None
        assert result.postcode == POSTCODE
        assert result.latitude == pytest.approx(LONDON_LAT, abs=0.05)
        assert result.admin_district == "Westminster"

    async def test_lookup_outcode(self, http_client):
        """A known UK outcode resolves correctly."""
        result = await lookup_outcode(OUTCODE, http_client)
        assert result is not None
        assert result.outcode == OUTCODE
        assert "Westminster" in result.admin_district

    async def test_unknown_postcode_returns_none(self, http_client):
        """An unknown postcode returns None."""
        result = await lookup_postcode("ZZ9Z 9ZZ", http_client)
        assert result is None


# ============================================================================
# FastAPI endpoint tests (no mocks — real upstream calls)
# ============================================================================


class TestGeocodingAPI:
    """Live tests for GET /geocode."""

    def test_geocode_coordinates(self, api_client: TestClient):
        """Coordinate query returns 200 with address data."""
        r = api_client.get("/geocode", params={"q": f"{LONDON_LAT},{LONDON_LON}"})
        assert r.status_code == 200
        data = r.json()
        assert data["geo"]["lat"] == pytest.approx(LONDON_LAT, abs=0.01)
        assert data["address"] is not None

    def test_geocode_place_name(self, api_client: TestClient):
        """Free-text place name returns 200."""
        r = api_client.get("/geocode", params={"q": "Manchester"})
        assert r.status_code == 200

    def test_geocode_not_found(self, api_client: TestClient):
        """Non-existent place returns 404."""
        r = api_client.get("/geocode", params={"q": "zzzzz-nonexistent-place"})
        assert r.status_code == 404


class TestRoutingAPI:
    """Live tests for POST /route."""

    def test_driving_route(self, api_client: TestClient):
        """Driving route returns 200 with at least one route."""
        r = api_client.post(
            "/route",
            json={
                "origin": {"lat": LONDON_LAT, "lon": LONDON_LON},
                "destination": {"lat": MANCHESTER_LAT, "lon": MANCHESTER_LON},
                "profile": "driving",
            },
        )
        assert r.status_code == 200
        data = r.json()
        assert data["profile"] == "driving"
        assert len(data["routes"]) >= 1

    def test_route_with_steps(self, api_client: TestClient):
        """Steps are present in the response when requested."""
        r = api_client.post(
            "/route",
            json={
                "origin": {"lat": LONDON_LAT, "lon": LONDON_LON},
                "destination": {"lat": MANCHESTER_LAT, "lon": MANCHESTER_LON},
                "steps": True,
            },
        )
        assert r.status_code == 200
        assert len(r.json()["routes"][0]["legs"][0]["steps"]) > 0


class TestPostcodesAPI:
    """Live tests for GET /postcodes and /outcodes."""

    def test_postcode_lookup(self, api_client: TestClient):
        """Known postcode returns 200 with normalised data."""
        r = api_client.get(f"/postcodes/{POSTCODE.replace(' ', '')}")
        assert r.status_code == 200
        assert r.json()["postcode"] == POSTCODE

    def test_outcode_lookup(self, api_client: TestClient):
        """Known outcode returns 200 with normalised data."""
        r = api_client.get(f"/outcodes/{OUTCODE}")
        assert r.status_code == 200
        assert r.json()["outcode"] == OUTCODE


class TestHealthAPI:
    """Live tests for GET /health."""

    def test_all_services_healthy(self, api_client: TestClient):
        """All backend services report healthy."""
        r = api_client.get("/health")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "healthy"
        for svc in data["services"].values():
            assert svc["status"] == "up"
            assert svc["latency_ms"] >= 0
