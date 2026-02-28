"""Routing helpers backed by OSRM via HAProxy."""

from __future__ import annotations

import httpx

from airgap_geo.geocoding import geocoder
from airgap_geo.models import (
    Address,
    GeoPoint,
    RouteLeg,
    RouteManoeuvre,
    RouteResult,
    RouteStep,
    RouteTurnStep,
)
from airgap_geo.settings import OSRM_API

_VALID_PROFILES = {"driving", "walking", "cycling"}
_VALID_GEOMETRIES = {"polyline", "polyline6", "geojson"}
_VALID_OVERVIEWS = {"full", "simplified", "false"}
_VALID_ANNOTATIONS = {"duration", "distance", "speed", "nodes", "weight", "datasources"}


def _build_params(
    steps: bool,
    alternatives: bool | int,
    annotations: list[str] | None,
    overview: str,
    geometries: str,
    continue_straight: bool | None,
    exclude: list[str] | None,
) -> dict[str, str]:
    """Build the OSRM query-parameter dict from the routing options."""
    params: dict[str, str] = {
        "overview": overview,
        "geometries": geometries,
    }
    if steps:
        params["steps"] = "true"
    if alternatives:
        params["alternatives"] = str(alternatives).lower()
    if annotations:
        params["annotations"] = ",".join(annotations)
    if continue_straight is not None:
        params["continue_straight"] = str(continue_straight).lower()
    if exclude:
        params["exclude"] = ",".join(exclude)
    return params


def _parse_manoeuvre(raw: dict) -> RouteManoeuvre | None:
    if not raw:
        return None
    loc = raw.get("location")
    return RouteManoeuvre(
        type=raw.get("type", ""),
        modifier=raw.get("modifier"),
        location=GeoPoint(lat=loc[1], lon=loc[0]) if loc else None,
        bearing_before=raw.get("bearing_before"),
        bearing_after=raw.get("bearing_after"),
    )


def _parse_leg(raw_leg: dict) -> RouteLeg:
    """Parse one OSRM route leg into a RouteLeg model."""
    raw_steps = raw_leg.get("steps", [])
    steps = [
        RouteTurnStep(
            distance_m=s.get("distance", 0.0),
            duration_s=s.get("duration", 0.0),
            geometry=s.get("geometry", ""),
            name=s.get("name", ""),
            manoeuvre=_parse_manoeuvre(s.get("maneuver", {})),
        )
        for s in raw_steps
    ]
    raw_annotation = raw_leg.get("annotation")
    return RouteLeg(
        distance_m=raw_leg.get("distance", 0.0),
        duration_s=raw_leg.get("duration", 0.0),
        steps=steps,
        annotation=raw_annotation,
    )


async def route(
    origin: tuple[float, float],
    destination: tuple[float, float],
    client: httpx.AsyncClient,
    profile: str = "driving",
    *,
    waypoints: list[tuple[float, float]] | None = None,
    steps: bool = False,
    alternatives: bool | int = False,
    annotations: list[str] | None = None,
    overview: str = "full",
    geometries: str = "polyline",
    continue_straight: bool | None = None,
    exclude: list[str] | None = None,
) -> RouteResult | None:
    """Calculate a route between two or more points using OSRM.

    Args:
        origin: ``(lat, lon)`` tuple for the start point.
        destination: ``(lat, lon)`` tuple for the end point.
        client: Shared async HTTP client.
        profile: One of ``"driving"``, ``"walking"``, or ``"cycling"``.
        waypoints: Optional list of intermediate ``(lat, lon)`` points.
        steps: If ``True``, include turn-by-turn manoeuvre steps per leg.
        alternatives: Request alternative routes. Pass ``True`` for any
            alternatives, or an integer for a specific count.
        annotations: List of per-segment annotation keys to include.
            Supported values: ``"duration"``, ``"distance"``, ``"speed"``,
            ``"nodes"``, ``"weight"``, ``"datasources"``.
        overview: Geometry detail level — ``"full"``, ``"simplified"``, or
            ``"false"`` (omit geometry entirely).
        geometries: Encoding for route geometry — ``"polyline"``,
            ``"polyline6"``, or ``"geojson"``.
        continue_straight: If ``True``, bias the route against U-turns at
            intermediate waypoints.
        exclude: Road classes to avoid, e.g. ``["motorway"]``, ``["toll"]``.

    Returns:
        A :class:`RouteResult` with normalised route steps and the raw OSRM
        response in ``raw``.  Returns ``None`` on request failure.

    Raises:
        ValueError: If *profile*, *overview*, or *geometries* is not one of
            the supported values, or if *annotations* contains unknown keys.
    """
    if profile not in _VALID_PROFILES:
        raise ValueError(
            f"Unsupported profile '{profile}'. Must be one of: "
            f"{', '.join(sorted(_VALID_PROFILES))}"
        )
    if overview not in _VALID_OVERVIEWS:
        raise ValueError(
            f"Unsupported overview '{overview}'. Must be one of: "
            f"{', '.join(sorted(_VALID_OVERVIEWS))}"
        )
    if geometries not in _VALID_GEOMETRIES:
        raise ValueError(
            f"Unsupported geometries '{geometries}'. Must be one of: "
            f"{', '.join(sorted(_VALID_GEOMETRIES))}"
        )
    if annotations:
        unknown = set(annotations) - _VALID_ANNOTATIONS
        if unknown:
            raise ValueError(
                f"Unknown annotation(s): {', '.join(sorted(unknown))}. "
                f"Supported: {', '.join(sorted(_VALID_ANNOTATIONS))}"
            )

    all_points = [origin, *(waypoints or []), destination]
    coordinates = ";".join(f"{lon},{lat}" for lat, lon in all_points)

    params = _build_params(
        steps=steps,
        alternatives=alternatives,
        annotations=annotations,
        overview=overview,
        geometries=geometries,
        continue_straight=continue_straight,
        exclude=exclude,
    )

    lat1, lon1 = origin
    lat2, lon2 = destination

    try:
        response = await client.get(
            f"{OSRM_API}/route/v1/{profile}/{coordinates}",
            params=params,
            timeout=30,
        )
        if not response.is_success:
            return None
        data = response.json()
    except Exception:
        return None

    # Parse snapped waypoints returned by OSRM
    snapped: list[GeoPoint] = []
    for wp in data.get("waypoints", []):
        loc = wp.get("location")
        if loc:
            snapped.append(GeoPoint(lat=loc[1], lon=loc[0]))

    # Build the requested intermediate waypoints list from input
    input_waypoints = [GeoPoint(lat=lat, lon=lon) for lat, lon in (waypoints or [])]

    route_steps = [
        RouteStep(
            distance_m=r.get("distance", 0.0),
            duration_s=r.get("duration", 0.0),
            geometry=r.get("geometry", ""),
            legs=[_parse_leg(leg) for leg in r.get("legs", [])],
        )
        for r in data.get("routes", [])
    ]

    return RouteResult(
        profile=profile,
        origin=GeoPoint(lat=lat1, lon=lon1),
        destination=GeoPoint(lat=lat2, lon=lon2),
        waypoints=input_waypoints,
        snapped_waypoints=snapped,
        routes=route_steps,
        raw=data,
    )


async def route_by_name(
    origin: str,
    destination: str,
    client: httpx.AsyncClient,
    profile: str = "driving",
    *,
    waypoints: list[str] | None = None,
    steps: bool = False,
    alternatives: bool | int = False,
    annotations: list[str] | None = None,
    overview: str = "full",
    geometries: str = "polyline",
    continue_straight: bool | None = None,
    exclude: list[str] | None = None,
) -> RouteResult:
    """Geocode text locations and calculate a route between them.

    Convenience wrapper around :func:`geocoder` and :func:`route`.  Each
    location string can be a free-text place name, postcode, or a
    ``"lat,lon"`` coordinate string — ``geocoder()`` handles detection
    automatically.

    Args:
        origin: Start location as free text or ``"lat,lon"``.
        destination: End location as free text or ``"lat,lon"``.
        client: Shared async HTTP client.
        profile: One of ``"driving"``, ``"walking"``, or ``"cycling"``.
        waypoints: Optional intermediate locations as text strings.
        steps: If ``True``, include turn-by-turn manoeuvre steps per leg.
        alternatives: Request alternative routes.
        annotations: Per-segment annotation keys to include.
        overview: Geometry detail level.
        geometries: Route geometry encoding.
        continue_straight: Bias against U-turns at waypoints.
        exclude: Road classes to avoid.

    Returns:
        A :class:`RouteResult` with ``origin_address``,
        ``destination_address``, and ``waypoint_addresses`` populated from
        the geocoding results.

    Raises:
        ValueError: If geocoding fails for any location, or if routing
            parameters are invalid.
    """
    origin_result = await geocoder(origin, client)
    if origin_result is None:
        raise ValueError(f"Could not geocode origin: '{origin}'")

    dest_result = await geocoder(destination, client)
    if dest_result is None:
        raise ValueError(f"Could not geocode destination: '{destination}'")

    origin_coords = (origin_result.geo.lat, origin_result.geo.lon)
    dest_coords = (dest_result.geo.lat, dest_result.geo.lon)

    wp_coords: list[tuple[float, float]] = []
    wp_addresses: list[Address] = []
    for wp_text in waypoints or []:
        wp_result = await geocoder(wp_text, client)
        if wp_result is None:
            raise ValueError(f"Could not geocode waypoint: '{wp_text}'")
        wp_coords.append((wp_result.geo.lat, wp_result.geo.lon))
        wp_addresses.append(wp_result.address or Address())

    result = await route(
        origin_coords,
        dest_coords,
        client,
        profile=profile,
        waypoints=wp_coords or None,
        steps=steps,
        alternatives=alternatives,
        annotations=annotations,
        overview=overview,
        geometries=geometries,
        continue_straight=continue_straight,
        exclude=exclude,
    )

    if result is None:
        raise ValueError(
            "Routing service returned no result after successful geocoding. "
            "Check OSRM is running."
        )

    result.origin_address = origin_result.address
    result.destination_address = dest_result.address
    result.waypoint_addresses = wp_addresses

    return result
