"""Tests for airgap_geocoding.routing."""

import pytest
import responses as responses_lib

from airgap_geocoding.routing import route
from airgap_geocoding.settings import OSRM_API

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


class TestRoute:
    """Tests for the route function."""

    @responses_lib.activate
    def test_happy_path_driving(self):
        """Returns parsed OSRM response for a driving route."""
        responses_lib.add(
            responses_lib.GET,
            f"{OSRM_API}/route/v1/driving/-0.1276,51.5034;-2.2426,53.4808",
            json=OSRM_RESPONSE,
            status=200,
        )
        result = route((51.5034, -0.1276), (53.4808, -2.2426), profile="driving")
        assert result["code"] == "Ok"
        assert len(result["routes"]) == 1

    @responses_lib.activate
    def test_happy_path_walking(self):
        """Returns parsed OSRM response for a walking route."""
        responses_lib.add(
            responses_lib.GET,
            f"{OSRM_API}/route/v1/walking/-0.1276,51.5034;-2.2426,53.4808",
            json=OSRM_RESPONSE,
            status=200,
        )
        result = route((51.5034, -0.1276), (53.4808, -2.2426), profile="walking")
        assert result["code"] == "Ok"

    @responses_lib.activate
    def test_happy_path_cycling(self):
        """Returns parsed OSRM response for a cycling route."""
        responses_lib.add(
            responses_lib.GET,
            f"{OSRM_API}/route/v1/cycling/-0.1276,51.5034;-2.2426,53.4808",
            json=OSRM_RESPONSE,
            status=200,
        )
        result = route((51.5034, -0.1276), (53.4808, -2.2426), profile="cycling")
        assert result["code"] == "Ok"

    def test_unsupported_profile_raises_value_error(self):
        """Raises ValueError for an unsupported profile name."""
        with pytest.raises(ValueError, match="Unsupported profile"):
            route((51.5034, -0.1276), (53.4808, -2.2426), profile="flying")

    @responses_lib.activate
    def test_non_200_returns_empty(self):
        """Returns empty dict when the OSRM API responds with a non-200 status."""
        responses_lib.add(
            responses_lib.GET,
            f"{OSRM_API}/route/v1/driving/-0.1276,51.5034;-2.2426,53.4808",
            json={"code": "NoRoute"},
            status=400,
        )
        result = route((51.5034, -0.1276), (53.4808, -2.2426))
        assert result == {}
