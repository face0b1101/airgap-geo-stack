"""Tests for POST /route."""

from __future__ import annotations

import re

import httpx
import pytest
from fastapi.testclient import TestClient

from airgap_geo.settings import NOMINATIM_URL, OSRM_API, PHOTON_API

_OSRM_BASE = str(httpx.URL(OSRM_API))

OSRM_RESPONSE = {
    "code": "Ok",
    "routes": [
        {
            "distance": 338210.6,
            "duration": 12754.3,
            "geometry": "encodedpolyline...",
            "legs": [],
        }
    ],
    "waypoints": [],
}

OSRM_RESPONSE_WITH_WAYPOINTS = {
    "code": "Ok",
    "routes": [
        {
            "distance": 5000.0,
            "duration": 600.0,
            "geometry": "polyline_wp",
            "legs": [
                {"distance": 2000.0, "duration": 240.0, "steps": []},
                {"distance": 3000.0, "duration": 360.0, "steps": []},
            ],
        }
    ],
    "waypoints": [
        {"location": [-0.1276, 51.5034], "name": "Origin"},
        {"location": [-0.09, 51.51], "name": "Via"},
        {"location": [-2.2426, 53.4808], "name": "Destination"},
    ],
}

OSRM_RESPONSE_WITH_STEPS = {
    "code": "Ok",
    "routes": [
        {
            "distance": 5000.0,
            "duration": 600.0,
            "geometry": "polyline_steps",
            "legs": [
                {
                    "distance": 5000.0,
                    "duration": 600.0,
                    "steps": [
                        {
                            "distance": 200.0,
                            "duration": 30.0,
                            "geometry": "sg1",
                            "name": "Baker Street",
                            "maneuver": {
                                "type": "depart",
                                "modifier": "straight",
                                "location": [-0.1276, 51.5034],
                                "bearing_before": 0,
                                "bearing_after": 90,
                            },
                        }
                    ],
                }
            ],
        }
    ],
    "waypoints": [],
}

OSRM_RESPONSE_ALTERNATIVES = {
    "code": "Ok",
    "routes": [
        {"distance": 5000.0, "duration": 600.0, "geometry": "alt1", "legs": []},
        {"distance": 6500.0, "duration": 750.0, "geometry": "alt2", "legs": []},
    ],
    "waypoints": [],
}

OSRM_RESPONSE_ANNOTATIONS = {
    "code": "Ok",
    "routes": [
        {
            "distance": 5000.0,
            "duration": 600.0,
            "geometry": "polyline_ann",
            "legs": [
                {
                    "distance": 5000.0,
                    "duration": 600.0,
                    "steps": [],
                    "annotation": {
                        "duration": [10.0, 20.0],
                        "distance": [100.0, 200.0],
                    },
                }
            ],
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

    def test_waypoints_in_request_returns_200(self, client: TestClient, httpx_mock):
        """A route request with intermediate waypoints returns 200."""
        httpx_mock.add_response(
            url=_OSRM_DRIVING_URL, json=OSRM_RESPONSE_WITH_WAYPOINTS, status_code=200
        )
        response = client.post(
            "/route",
            json={
                "origin": _ORIGIN,
                "destination": _DEST,
                "waypoints": [{"lat": 51.51, "lon": -0.09}],
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["waypoints"]) == 1
        assert data["waypoints"][0]["lat"] == 51.51
        assert len(data["snapped_waypoints"]) == 3
        assert len(data["routes"][0]["legs"]) == 2

    def test_steps_option_included_in_response(self, client: TestClient, httpx_mock):
        """Turn-by-turn steps are included in the response when steps=true."""
        httpx_mock.add_response(
            url=_OSRM_DRIVING_URL, json=OSRM_RESPONSE_WITH_STEPS, status_code=200
        )
        response = client.post(
            "/route",
            json={"origin": _ORIGIN, "destination": _DEST, "steps": True},
        )
        assert response.status_code == 200
        leg = response.json()["routes"][0]["legs"][0]
        assert len(leg["steps"]) == 1
        assert leg["steps"][0]["name"] == "Baker Street"
        assert leg["steps"][0]["manoeuvre"]["type"] == "depart"

    def test_alternatives_returns_multiple_routes(self, client: TestClient, httpx_mock):
        """alternatives=true returns more than one route in the response."""
        httpx_mock.add_response(
            url=_OSRM_DRIVING_URL, json=OSRM_RESPONSE_ALTERNATIVES, status_code=200
        )
        response = client.post(
            "/route",
            json={"origin": _ORIGIN, "destination": _DEST, "alternatives": True},
        )
        assert response.status_code == 200
        assert len(response.json()["routes"]) == 2

    def test_annotations_in_response(self, client: TestClient, httpx_mock):
        """Annotations are present in leg data when requested."""
        httpx_mock.add_response(
            url=_OSRM_DRIVING_URL, json=OSRM_RESPONSE_ANNOTATIONS, status_code=200
        )
        response = client.post(
            "/route",
            json={
                "origin": _ORIGIN,
                "destination": _DEST,
                "annotations": ["duration", "distance"],
            },
        )
        assert response.status_code == 200
        leg = response.json()["routes"][0]["legs"][0]
        assert leg["annotation"]["duration"] == [10.0, 20.0]

    def test_invalid_annotation_returns_422(self, client: TestClient, httpx_mock):
        """An unknown annotation key fails FastAPI validation with 422."""
        response = client.post(
            "/route",
            json={"origin": _ORIGIN, "destination": _DEST, "annotations": ["badkey"]},
        )
        assert response.status_code == 422

    def test_different_options_produce_separate_cache_entries(
        self, client: TestClient, httpx_mock
    ):
        """Requests with different options are cached independently."""
        httpx_mock.add_response(
            url=_OSRM_DRIVING_URL, json=OSRM_RESPONSE, status_code=200
        )
        httpx_mock.add_response(
            url=_OSRM_DRIVING_URL, json=OSRM_RESPONSE, status_code=200
        )
        body_a = {"origin": _ORIGIN, "destination": _DEST, "steps": False}
        body_b = {"origin": _ORIGIN, "destination": _DEST, "steps": True}
        client.post("/route", json=body_a)
        client.post("/route", json=body_b)
        # Both are cache misses — two separate OSRM requests
        assert len(httpx_mock.get_requests()) == 2

    def test_exclude_option_passes_through(self, client: TestClient, httpx_mock):
        """Exclude option is accepted and request succeeds."""
        httpx_mock.add_response(
            url=_OSRM_DRIVING_URL, json=OSRM_RESPONSE, status_code=200
        )
        response = client.post(
            "/route",
            json={"origin": _ORIGIN, "destination": _DEST, "exclude": ["motorway"]},
        )
        assert response.status_code == 200
        req_url = str(httpx_mock.get_requests()[0].url)
        assert "exclude=motorway" in req_url

    def test_geometries_option_passes_through(self, client: TestClient, httpx_mock):
        """Geometries option is accepted and passed to OSRM."""
        httpx_mock.add_response(
            url=_OSRM_DRIVING_URL, json=OSRM_RESPONSE, status_code=200
        )
        response = client.post(
            "/route",
            json={"origin": _ORIGIN, "destination": _DEST, "geometries": "geojson"},
        )
        assert response.status_code == 200
        req_url = str(httpx_mock.get_requests()[0].url)
        assert "geometries=geojson" in req_url


# ---------------------------------------------------------------------------
# Smart endpoint tests — text / mixed input
# ---------------------------------------------------------------------------

_NOMINATIM_SEARCH_URL = re.compile(rf"{re.escape(NOMINATIM_URL)}/search.*")
_PHOTON_REVERSE_URL = re.compile(rf"{re.escape(PHOTON_API)}/reverse.*")

_NOMINATIM_WESTMINSTER = [
    {"place_id": 10, "lat": "51.4975", "lon": "-0.1357", "display_name": "Westminster"}
]
_NOMINATIM_BIRMINGHAM = [
    {"place_id": 20, "lat": "52.4862", "lon": "-1.8904", "display_name": "Birmingham"}
]

_PHOTON_WESTMINSTER = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [-0.1357, 51.4975]},
            "properties": {
                "name": "Westminster",
                "city": "London",
                "country": "United Kingdom",
                "countrycode": "GB",
            },
        }
    ],
}
_PHOTON_BIRMINGHAM = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [-1.8904, 52.4862]},
            "properties": {
                "name": "Birmingham",
                "city": "Birmingham",
                "country": "United Kingdom",
                "countrycode": "GB",
            },
        }
    ],
}


def _mock_geocode_westminster(httpx_mock) -> None:
    """Register Nominatim + Photon mocks for 'Westminster'."""
    httpx_mock.add_response(
        url=_NOMINATIM_SEARCH_URL, json=_NOMINATIM_WESTMINSTER, status_code=200
    )
    httpx_mock.add_response(
        url=_PHOTON_REVERSE_URL, json=_PHOTON_WESTMINSTER, status_code=200
    )


def _mock_geocode_birmingham(httpx_mock) -> None:
    """Register Nominatim + Photon mocks for 'Birmingham'."""
    httpx_mock.add_response(
        url=_NOMINATIM_SEARCH_URL, json=_NOMINATIM_BIRMINGHAM, status_code=200
    )
    httpx_mock.add_response(
        url=_PHOTON_REVERSE_URL, json=_PHOTON_BIRMINGHAM, status_code=200
    )


class TestSmartRouteEndpoint:
    """Tests for POST /route with text-based origin/destination."""

    def test_text_origin_and_destination(self, client: TestClient, httpx_mock):
        """Text inputs are geocoded and a route is returned with address metadata."""
        _mock_geocode_westminster(httpx_mock)
        _mock_geocode_birmingham(httpx_mock)
        httpx_mock.add_response(
            url=_OSRM_DRIVING_URL, json=OSRM_RESPONSE, status_code=200
        )

        response = client.post(
            "/route",
            json={"origin": "Westminster", "destination": "Birmingham"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["origin"]["lat"] == pytest.approx(51.4975, abs=1e-3)
        assert data["destination"]["lat"] == pytest.approx(52.4862, abs=1e-3)
        assert data["origin_address"]["city"] == "London"
        assert data["destination_address"]["city"] == "Birmingham"
        assert len(data["routes"]) == 1

    def test_mixed_geopoint_origin_text_destination(
        self, client: TestClient, httpx_mock
    ):
        """GeoPoint origin + text destination works in a single request."""
        _mock_geocode_birmingham(httpx_mock)
        httpx_mock.add_response(
            url=_OSRM_DRIVING_URL, json=OSRM_RESPONSE, status_code=200
        )

        response = client.post(
            "/route",
            json={"origin": _ORIGIN, "destination": "Birmingham"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["origin"]["lat"] == _ORIGIN["lat"]
        assert data["origin_address"] is None
        assert data["destination_address"]["city"] == "Birmingham"

    def test_mixed_text_origin_geopoint_destination(
        self, client: TestClient, httpx_mock
    ):
        """Text origin + GeoPoint destination works in a single request."""
        _mock_geocode_westminster(httpx_mock)
        httpx_mock.add_response(
            url=_OSRM_DRIVING_URL, json=OSRM_RESPONSE, status_code=200
        )

        response = client.post(
            "/route",
            json={"origin": "Westminster", "destination": _DEST},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["origin_address"]["city"] == "London"
        assert data["destination_address"] is None
        assert data["destination"]["lat"] == _DEST["lat"]

    def test_geocode_failure_returns_422(self, client: TestClient, httpx_mock):
        """Returns 422 when a text location cannot be geocoded."""
        httpx_mock.add_response(url=_NOMINATIM_SEARCH_URL, json=[], status_code=200)

        response = client.post(
            "/route",
            json={"origin": "Atlantis", "destination": _DEST},
        )
        assert response.status_code == 422
        assert "Could not geocode origin" in response.json()["detail"]

    def test_text_route_cached_on_resolved_coords(self, client: TestClient, httpx_mock):
        """Repeated text requests hit the cache after the first geocode + route."""
        _mock_geocode_westminster(httpx_mock)
        _mock_geocode_birmingham(httpx_mock)
        httpx_mock.add_response(
            url=_OSRM_DRIVING_URL, json=OSRM_RESPONSE, status_code=200
        )
        _mock_geocode_westminster(httpx_mock)
        _mock_geocode_birmingham(httpx_mock)

        body = {"origin": "Westminster", "destination": "Birmingham"}
        client.post("/route", json=body)
        client.post("/route", json=body)

        osrm_requests = [
            r for r in httpx_mock.get_requests() if "/route/v1/" in str(r.url)
        ]
        assert len(osrm_requests) == 1

    def test_coordinate_only_requests_still_work(self, client: TestClient, httpx_mock):
        """Existing coordinate-only requests remain fully backwards compatible."""
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
        assert data["origin_address"] is None
        assert data["destination_address"] is None
        assert data["waypoint_addresses"] == []
