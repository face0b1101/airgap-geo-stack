"""Tests for airgap_geocoding.geocoding."""

import pytest
import responses as responses_lib

from airgap_geocoding.geocoding import (
    geocoder,
    nominatim_geocoder,
    photon_reverse_geocode,
)
from airgap_geocoding.settings import NOMINATIM_URL, PHOTON_API

PHOTON_FEATURE = {
    "type": "Feature",
    "geometry": {"type": "Point", "coordinates": [-0.1276, 51.5034]},
    "properties": {
        "name": "10 Downing Street",
        "city": "London",
        "country": "United Kingdom",
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


class TestPhotonReverseGeocode:
    """Tests for photon_reverse_geocode."""

    @responses_lib.activate
    def test_happy_path(self):
        """Returns the first feature on a successful response."""
        responses_lib.add(
            responses_lib.GET,
            f"{PHOTON_API}/reverse",
            json=PHOTON_RESPONSE,
            status=200,
        )
        result = photon_reverse_geocode(51.5034, -0.1276)
        assert result == PHOTON_FEATURE

    @responses_lib.activate
    def test_non_200_returns_empty(self):
        """Returns empty dict when the API responds with a non-200 status."""
        responses_lib.add(
            responses_lib.GET,
            f"{PHOTON_API}/reverse",
            json={"error": "not found"},
            status=404,
        )
        result = photon_reverse_geocode(51.5034, -0.1276)
        assert result == {}

    @responses_lib.activate
    def test_empty_features_returns_empty(self):
        """Returns empty dict when the features list is empty."""
        responses_lib.add(
            responses_lib.GET,
            f"{PHOTON_API}/reverse",
            json={"type": "FeatureCollection", "features": []},
            status=200,
        )
        result = photon_reverse_geocode(51.5034, -0.1276)
        assert result == {}


class TestNominatimGeocoder:
    """Tests for nominatim_geocoder."""

    @responses_lib.activate
    def test_happy_path(self):
        """Returns the first result on a successful response."""
        responses_lib.add(
            responses_lib.GET,
            f"{NOMINATIM_URL}/search",
            json=NOMINATIM_RESULT,
            status=200,
        )
        result = nominatim_geocoder("10 Downing Street London")
        assert result["lat"] == "51.5034"
        assert result["lon"] == "-0.1276"

    @responses_lib.activate
    def test_non_200_returns_empty(self):
        """Returns empty dict when the API responds with a non-200 status."""
        responses_lib.add(
            responses_lib.GET,
            f"{NOMINATIM_URL}/search",
            json={"error": "server error"},
            status=500,
        )
        result = nominatim_geocoder("Nowhere")
        assert result == {}

    @responses_lib.activate
    def test_empty_results_returns_empty(self):
        """Returns empty dict when no results are returned."""
        responses_lib.add(
            responses_lib.GET,
            f"{NOMINATIM_URL}/search",
            json=[],
            status=200,
        )
        result = nominatim_geocoder("zzz-does-not-exist")
        assert result == {}


class TestGeocoder:
    """Tests for geocoder."""

    @responses_lib.activate
    def test_coordinate_string_input(self):
        """Parses a lat,lon string and reverse geocodes without hitting Nominatim."""
        responses_lib.add(
            responses_lib.GET,
            f"{PHOTON_API}/reverse",
            json=PHOTON_RESPONSE,
            status=200,
        )
        result = geocoder("51.5034,-0.1276")
        assert result["geo"] == {"lat": 51.5034, "lon": -0.1276}
        assert result["type"] == "Feature"

    @responses_lib.activate
    def test_place_name_input(self):
        """Geocodes a place name via Nominatim then enriches via Photon."""
        responses_lib.add(
            responses_lib.GET,
            f"{NOMINATIM_URL}/search",
            json=NOMINATIM_RESULT,
            status=200,
        )
        responses_lib.add(
            responses_lib.GET,
            f"{PHOTON_API}/reverse",
            json=PHOTON_RESPONSE,
            status=200,
        )
        result = geocoder("10 Downing Street London")
        assert result["geo"]["lat"] == pytest.approx(51.5034, abs=1e-4)
        assert result["geo"]["lon"] == pytest.approx(-0.1276, abs=1e-4)

    @responses_lib.activate
    def test_invalid_coords_fall_through_to_nominatim(self):
        """Out-of-range coordinates are treated as a place-name query."""
        responses_lib.add(
            responses_lib.GET,
            f"{NOMINATIM_URL}/search",
            json=NOMINATIM_RESULT,
            status=200,
        )
        responses_lib.add(
            responses_lib.GET,
            f"{PHOTON_API}/reverse",
            json=PHOTON_RESPONSE,
            status=200,
        )
        # lat=999 is out of range - should fall through to Nominatim
        result = geocoder("999,-0.1276")
        assert "geo" in result

    @responses_lib.activate
    def test_empty_nominatim_result_returns_empty(self):
        """Returns empty dict when Nominatim finds no matching location."""
        responses_lib.add(
            responses_lib.GET,
            f"{NOMINATIM_URL}/search",
            json=[],
            status=200,
        )
        result = geocoder("zzz-does-not-exist")
        assert result == {}
