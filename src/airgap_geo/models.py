"""Normalised Pydantic response models for airgap_geo."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict


class GeoPoint(BaseModel):
    """A latitude/longitude coordinate pair."""

    model_config = ConfigDict(frozen=True)

    lat: float
    lon: float


class Address(BaseModel):
    """Normalised address fields extracted from Photon/Nominatim properties."""

    model_config = ConfigDict(frozen=True)

    name: str | None = None
    house_number: str | None = None
    street: str | None = None
    postcode: str | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = None
    country_code: str | None = None


class GeocodeResult(BaseModel):
    """Normalised result from a geocode or reverse-geocode operation."""

    geo: GeoPoint
    address: Address | None = None
    raw: dict[str, Any] = {}


class RouteManoeuvre(BaseModel):
    """A single turn or manoeuvre instruction from an OSRM step."""

    model_config = ConfigDict(frozen=True)

    type: str
    modifier: str | None = None
    location: GeoPoint | None = None
    bearing_before: int | None = None
    bearing_after: int | None = None


class RouteTurnStep(BaseModel):
    """One navigation step within a route leg (when steps=True is requested)."""

    model_config = ConfigDict(frozen=True)

    distance_m: float
    duration_s: float
    geometry: str
    name: str
    manoeuvre: RouteManoeuvre | None = None


class RouteLeg(BaseModel):
    """One leg of a route (segment between two consecutive waypoints)."""

    distance_m: float
    duration_s: float
    steps: list[RouteTurnStep] = []
    annotation: dict[str, Any] | None = None


class RouteStep(BaseModel):
    """Summary of a single route returned by OSRM."""

    model_config = ConfigDict(frozen=True)

    distance_m: float
    duration_s: float
    geometry: str
    legs: list[RouteLeg] = []


class RouteResult(BaseModel):
    """Normalised result from a routing operation."""

    profile: str
    origin: GeoPoint
    destination: GeoPoint
    origin_address: Address | None = None
    destination_address: Address | None = None
    waypoints: list[GeoPoint] = []
    waypoint_addresses: list[Address] = []
    snapped_waypoints: list[GeoPoint] = []
    routes: list[RouteStep] = []
    raw: dict[str, Any] = {}


class PostcodeResult(BaseModel):
    """Normalised result from a UK postcode lookup."""

    postcode: str
    latitude: float | None = None
    longitude: float | None = None
    admin_district: str | None = None
    admin_county: str | None = None
    admin_ward: str | None = None
    parish: str | None = None
    region: str | None = None
    country: str | None = None
    primary_care_trust: str | None = None
    lsoa: str | None = None
    msoa: str | None = None
    nuts: str | None = None
    codes: dict[str, Any] = {}
    raw: dict[str, Any] = {}


class OutcodeResult(BaseModel):
    """Normalised result from a UK outcode (district) lookup."""

    outcode: str
    latitude: float | None = None
    longitude: float | None = None
    admin_district: list[str] = []
    parish: list[str] = []
    admin_county: list[str] = []
    admin_ward: list[str] = []
    country: list[str] = []
    raw: dict[str, Any] = {}
