"""Tests for airgap_geo.routing."""

from __future__ import annotations

import re

import httpx
import pytest

from airgap_geo.routing import route
from airgap_geo.settings import OSRM_API

# httpx normalises default ports (e.g. http://host:80 → http://host), so we
# must match against the normalised form when building URL patterns.
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

_OSRM_DRIVING_URL = re.compile(rf"{re.escape(_OSRM_BASE)}/route/v1/driving.*")
_OSRM_WALKING_URL = re.compile(rf"{re.escape(_OSRM_BASE)}/route/v1/walking.*")
_OSRM_CYCLING_URL = re.compile(rf"{re.escape(_OSRM_BASE)}/route/v1/cycling.*")


class TestRoute:
    """Tests for the route function."""

    async def test_happy_path_driving(self, httpx_mock):
        """Returns a RouteResult for a driving route."""
        httpx_mock.add_response(
            url=_OSRM_DRIVING_URL, json=OSRM_RESPONSE, status_code=200
        )
        async with httpx.AsyncClient() as client:
            result = await route(
                (51.5034, -0.1276), (53.4808, -2.2426), client, profile="driving"
            )
        assert result is not None
        assert result.profile == "driving"
        assert len(result.routes) == 1
        assert result.routes[0].distance_m == pytest.approx(338210.6)
        assert result.routes[0].duration_s == pytest.approx(12754.3)
        assert result.routes[0].geometry == "encodedpolyline..."

    async def test_happy_path_walking(self, httpx_mock):
        """Returns a RouteResult for a walking route."""
        httpx_mock.add_response(
            url=_OSRM_WALKING_URL, json=OSRM_RESPONSE, status_code=200
        )
        async with httpx.AsyncClient() as client:
            result = await route(
                (51.5034, -0.1276), (53.4808, -2.2426), client, profile="walking"
            )
        assert result is not None
        assert result.profile == "walking"

    async def test_happy_path_cycling(self, httpx_mock):
        """Returns a RouteResult for a cycling route."""
        httpx_mock.add_response(
            url=_OSRM_CYCLING_URL, json=OSRM_RESPONSE, status_code=200
        )
        async with httpx.AsyncClient() as client:
            result = await route(
                (51.5034, -0.1276), (53.4808, -2.2426), client, profile="cycling"
            )
        assert result is not None
        assert result.profile == "cycling"

    async def test_unsupported_profile_raises_value_error(self):
        """Raises ValueError for an unsupported profile name."""
        async with httpx.AsyncClient() as client:
            with pytest.raises(ValueError, match="Unsupported profile"):
                await route(
                    (51.5034, -0.1276), (53.4808, -2.2426), client, profile="flying"
                )

    async def test_non_200_returns_none(self, httpx_mock):
        """Returns None when the OSRM API responds with a non-200 status."""
        httpx_mock.add_response(
            url=_OSRM_DRIVING_URL, json={"code": "NoRoute"}, status_code=400
        )
        async with httpx.AsyncClient() as client:
            result = await route((51.5034, -0.1276), (53.4808, -2.2426), client)
        assert result is None

    async def test_origin_destination_stored(self, httpx_mock):
        """Origin and destination GeoPoints are preserved on the result."""
        httpx_mock.add_response(
            url=_OSRM_DRIVING_URL, json=OSRM_RESPONSE, status_code=200
        )
        async with httpx.AsyncClient() as client:
            result = await route((51.5034, -0.1276), (53.4808, -2.2426), client)
        assert result is not None
        assert result.origin.lat == pytest.approx(51.5034)
        assert result.destination.lat == pytest.approx(53.4808)

    async def test_raw_field_preserved(self, httpx_mock):
        """The raw OSRM response is preserved in result.raw."""
        httpx_mock.add_response(
            url=_OSRM_DRIVING_URL, json=OSRM_RESPONSE, status_code=200
        )
        async with httpx.AsyncClient() as client:
            result = await route((51.5034, -0.1276), (53.4808, -2.2426), client)
        assert result is not None
        assert result.raw["code"] == "Ok"
