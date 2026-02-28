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
            "legs": [],
        }
    ],
    "waypoints": [],
}

# OSRM response that includes a snapped waypoint location
OSRM_RESPONSE_WITH_WAYPOINTS = {
    "code": "Ok",
    "routes": [
        {
            "distance": 5000.0,
            "duration": 600.0,
            "geometry": "polyline_abc",
            "legs": [
                {"distance": 2000.0, "duration": 240.0, "steps": []},
                {"distance": 3000.0, "duration": 360.0, "steps": []},
            ],
        }
    ],
    "waypoints": [
        {"location": [-0.1276, 51.5034], "name": "Origin"},
        {"location": [-0.0900, 51.5100], "name": "Waypoint"},
        {"location": [-2.2426, 53.4808], "name": "Destination"},
    ],
}

# OSRM response with steps and manoeuvres
OSRM_RESPONSE_WITH_STEPS = {
    "code": "Ok",
    "routes": [
        {
            "distance": 5000.0,
            "duration": 600.0,
            "geometry": "polyline_xyz",
            "legs": [
                {
                    "distance": 5000.0,
                    "duration": 600.0,
                    "steps": [
                        {
                            "distance": 200.0,
                            "duration": 30.0,
                            "geometry": "step_geom_1",
                            "name": "Baker Street",
                            "maneuver": {
                                "type": "depart",
                                "modifier": "straight",
                                "location": [-0.1276, 51.5034],
                                "bearing_before": 0,
                                "bearing_after": 90,
                            },
                        },
                        {
                            "distance": 4800.0,
                            "duration": 570.0,
                            "geometry": "step_geom_2",
                            "name": "Marylebone Road",
                            "maneuver": {
                                "type": "turn",
                                "modifier": "right",
                                "location": [-0.1300, 51.5050],
                                "bearing_before": 90,
                                "bearing_after": 0,
                            },
                        },
                    ],
                }
            ],
        }
    ],
    "waypoints": [
        {"location": [-0.1276, 51.5034], "name": "Origin"},
        {"location": [-2.2426, 53.4808], "name": "Destination"},
    ],
}

# OSRM response with annotations
OSRM_RESPONSE_WITH_ANNOTATIONS = {
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
                        "duration": [10.5, 20.3, 15.1],
                        "distance": [100.0, 200.0, 150.0],
                    },
                }
            ],
        }
    ],
    "waypoints": [],
}

# Two alternative routes
OSRM_RESPONSE_ALTERNATIVES = {
    "code": "Ok",
    "routes": [
        {
            "distance": 5000.0,
            "duration": 600.0,
            "geometry": "polyline_alt1",
            "legs": [],
        },
        {
            "distance": 6000.0,
            "duration": 720.0,
            "geometry": "polyline_alt2",
            "legs": [],
        },
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

    async def test_waypoints_included_in_coordinates(self, httpx_mock):
        """Intermediate waypoints are included in the OSRM coordinate string."""
        httpx_mock.add_response(
            url=_OSRM_DRIVING_URL, json=OSRM_RESPONSE_WITH_WAYPOINTS, status_code=200
        )
        async with httpx.AsyncClient() as client:
            result = await route(
                (51.5034, -0.1276),
                (53.4808, -2.2426),
                client,
                waypoints=[(51.51, -0.09)],
            )
        assert result is not None
        # Verify the waypoint is stored on the result
        assert len(result.waypoints) == 1
        assert result.waypoints[0].lat == pytest.approx(51.51)
        assert result.waypoints[0].lon == pytest.approx(-0.09)
        # Request should have had three coordinates in the URL
        req_url = str(httpx_mock.get_requests()[0].url)
        assert req_url.count(";") == 2  # three coords = two semicolons

    async def test_snapped_waypoints_from_osrm_response(self, httpx_mock):
        """Snapped waypoints from the OSRM response are parsed correctly."""
        httpx_mock.add_response(
            url=_OSRM_DRIVING_URL, json=OSRM_RESPONSE_WITH_WAYPOINTS, status_code=200
        )
        async with httpx.AsyncClient() as client:
            result = await route(
                (51.5034, -0.1276),
                (53.4808, -2.2426),
                client,
                waypoints=[(51.51, -0.09)],
            )
        assert result is not None
        assert len(result.snapped_waypoints) == 3
        assert result.snapped_waypoints[0].lat == pytest.approx(51.5034)
        assert result.snapped_waypoints[0].lon == pytest.approx(-0.1276)

    async def test_multi_waypoint_legs_parsed(self, httpx_mock):
        """Each route leg is parsed into a RouteLeg model."""
        httpx_mock.add_response(
            url=_OSRM_DRIVING_URL, json=OSRM_RESPONSE_WITH_WAYPOINTS, status_code=200
        )
        async with httpx.AsyncClient() as client:
            result = await route(
                (51.5034, -0.1276),
                (53.4808, -2.2426),
                client,
                waypoints=[(51.51, -0.09)],
            )
        assert result is not None
        assert len(result.routes) == 1
        legs = result.routes[0].legs
        assert len(legs) == 2
        assert legs[0].distance_m == pytest.approx(2000.0)
        assert legs[1].distance_m == pytest.approx(3000.0)

    async def test_steps_parsed_into_turn_steps(self, httpx_mock):
        """Turn-by-turn steps are parsed into RouteTurnStep models when present."""
        httpx_mock.add_response(
            url=_OSRM_DRIVING_URL, json=OSRM_RESPONSE_WITH_STEPS, status_code=200
        )
        async with httpx.AsyncClient() as client:
            result = await route(
                (51.5034, -0.1276),
                (53.4808, -2.2426),
                client,
                steps=True,
            )
        assert result is not None
        leg = result.routes[0].legs[0]
        assert len(leg.steps) == 2
        assert leg.steps[0].name == "Baker Street"
        assert leg.steps[0].manoeuvre is not None
        assert leg.steps[0].manoeuvre.type == "depart"
        assert leg.steps[0].manoeuvre.modifier == "straight"
        assert leg.steps[0].manoeuvre.location is not None
        assert leg.steps[0].manoeuvre.location.lat == pytest.approx(51.5034)
        assert leg.steps[1].manoeuvre is not None
        assert leg.steps[1].manoeuvre.type == "turn"
        assert leg.steps[1].manoeuvre.modifier == "right"

    async def test_steps_request_param_sent(self, httpx_mock):
        """steps=True is passed as a query parameter to OSRM."""
        httpx_mock.add_response(
            url=_OSRM_DRIVING_URL, json=OSRM_RESPONSE_WITH_STEPS, status_code=200
        )
        async with httpx.AsyncClient() as client:
            await route(
                (51.5034, -0.1276),
                (53.4808, -2.2426),
                client,
                steps=True,
            )
        req_url = str(httpx_mock.get_requests()[0].url)
        assert "steps=true" in req_url

    async def test_alternatives_request_param_sent(self, httpx_mock):
        """alternatives=True is passed as a query parameter to OSRM."""
        httpx_mock.add_response(
            url=_OSRM_DRIVING_URL, json=OSRM_RESPONSE_ALTERNATIVES, status_code=200
        )
        async with httpx.AsyncClient() as client:
            result = await route(
                (51.5034, -0.1276),
                (53.4808, -2.2426),
                client,
                alternatives=True,
            )
        req_url = str(httpx_mock.get_requests()[0].url)
        assert "alternatives=true" in req_url
        assert result is not None
        assert len(result.routes) == 2

    async def test_annotations_parsed_onto_leg(self, httpx_mock):
        """Per-segment annotations from OSRM are stored on RouteLeg.annotation."""
        httpx_mock.add_response(
            url=_OSRM_DRIVING_URL, json=OSRM_RESPONSE_WITH_ANNOTATIONS, status_code=200
        )
        async with httpx.AsyncClient() as client:
            result = await route(
                (51.5034, -0.1276),
                (53.4808, -2.2426),
                client,
                annotations=["duration", "distance"],
            )
        assert result is not None
        leg = result.routes[0].legs[0]
        assert leg.annotation is not None
        assert leg.annotation["duration"] == [10.5, 20.3, 15.1]
        assert leg.annotation["distance"] == [100.0, 200.0, 150.0]

    async def test_annotations_request_param_sent(self, httpx_mock):
        """Annotations list is joined and passed as a query parameter to OSRM."""
        httpx_mock.add_response(
            url=_OSRM_DRIVING_URL, json=OSRM_RESPONSE_WITH_ANNOTATIONS, status_code=200
        )
        async with httpx.AsyncClient() as client:
            await route(
                (51.5034, -0.1276),
                (53.4808, -2.2426),
                client,
                annotations=["duration", "distance"],
            )
        req_url = str(httpx_mock.get_requests()[0].url)
        assert "annotations=" in req_url

    async def test_exclude_request_param_sent(self, httpx_mock):
        """Exclude list is joined and passed as a query parameter to OSRM."""
        httpx_mock.add_response(
            url=_OSRM_DRIVING_URL, json=OSRM_RESPONSE, status_code=200
        )
        async with httpx.AsyncClient() as client:
            await route(
                (51.5034, -0.1276),
                (53.4808, -2.2426),
                client,
                exclude=["motorway"],
            )
        req_url = str(httpx_mock.get_requests()[0].url)
        assert "exclude=motorway" in req_url

    async def test_geometries_param_sent(self, httpx_mock):
        """Geometries parameter is passed through to OSRM."""
        httpx_mock.add_response(
            url=_OSRM_DRIVING_URL, json=OSRM_RESPONSE, status_code=200
        )
        async with httpx.AsyncClient() as client:
            await route(
                (51.5034, -0.1276),
                (53.4808, -2.2426),
                client,
                geometries="geojson",
            )
        req_url = str(httpx_mock.get_requests()[0].url)
        assert "geometries=geojson" in req_url

    async def test_overview_param_sent(self, httpx_mock):
        """Overview parameter is passed through to OSRM."""
        httpx_mock.add_response(
            url=_OSRM_DRIVING_URL, json=OSRM_RESPONSE, status_code=200
        )
        async with httpx.AsyncClient() as client:
            await route(
                (51.5034, -0.1276),
                (53.4808, -2.2426),
                client,
                overview="simplified",
            )
        req_url = str(httpx_mock.get_requests()[0].url)
        assert "overview=simplified" in req_url

    async def test_continue_straight_param_sent(self, httpx_mock):
        """continue_straight parameter is passed through to OSRM."""
        httpx_mock.add_response(
            url=_OSRM_DRIVING_URL, json=OSRM_RESPONSE, status_code=200
        )
        async with httpx.AsyncClient() as client:
            await route(
                (51.5034, -0.1276),
                (53.4808, -2.2426),
                client,
                continue_straight=True,
            )
        req_url = str(httpx_mock.get_requests()[0].url)
        assert "continue_straight=true" in req_url

    async def test_unsupported_overview_raises_value_error(self):
        """Raises ValueError for an unsupported overview value."""
        async with httpx.AsyncClient() as client:
            with pytest.raises(ValueError, match="Unsupported overview"):
                await route(
                    (51.5034, -0.1276), (53.4808, -2.2426), client, overview="detailed"
                )

    async def test_unsupported_geometries_raises_value_error(self):
        """Raises ValueError for an unsupported geometries value."""
        async with httpx.AsyncClient() as client:
            with pytest.raises(ValueError, match="Unsupported geometries"):
                await route(
                    (51.5034, -0.1276), (53.4808, -2.2426), client, geometries="wkt"
                )

    async def test_unknown_annotation_raises_value_error(self):
        """Raises ValueError for an unknown annotation key."""
        async with httpx.AsyncClient() as client:
            with pytest.raises(ValueError, match="Unknown annotation"):
                await route(
                    (51.5034, -0.1276),
                    (53.4808, -2.2426),
                    client,
                    annotations=["duration", "badkey"],
                )

    async def test_no_waypoints_field_is_empty_list(self, httpx_mock):
        """Waypoints field on RouteResult is empty when none are provided."""
        httpx_mock.add_response(
            url=_OSRM_DRIVING_URL, json=OSRM_RESPONSE, status_code=200
        )
        async with httpx.AsyncClient() as client:
            result = await route((51.5034, -0.1276), (53.4808, -2.2426), client)
        assert result is not None
        assert result.waypoints == []
