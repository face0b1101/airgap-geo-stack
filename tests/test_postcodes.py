"""Tests for airgap_geocoding.postcodes."""

import responses as responses_lib

from airgap_geocoding.postcodes import lookup_outcode, lookup_postcode
from airgap_geocoding.settings import POSTCODES_URL

POSTCODE_RESULT = {
    "postcode": "SW1A 2AA",
    "latitude": 51.5034,
    "longitude": -0.1276,
    "admin_district": "Westminster",
}

OUTCODE_RESULT = {
    "outcode": "SW1A",
    "latitude": 51.5028,
    "longitude": -0.1306,
}


class TestLookupPostcode:
    """Tests for lookup_postcode."""

    @responses_lib.activate
    def test_happy_path(self):
        """Returns the result dict on a successful postcodes.io response."""
        responses_lib.add(
            responses_lib.GET,
            f"{POSTCODES_URL}/postcodes/SW1A2AA",
            json={"status": 200, "result": POSTCODE_RESULT},
            status=200,
        )
        result = lookup_postcode("SW1A2AA")
        assert result["postcode"] == "SW1A 2AA"
        assert result["latitude"] == 51.5034

    @responses_lib.activate
    def test_non_200_returns_empty(self):
        """Returns empty dict when the API responds with a non-200 status."""
        responses_lib.add(
            responses_lib.GET,
            f"{POSTCODES_URL}/postcodes/INVALID",
            json={"status": 404, "error": "Postcode not found"},
            status=404,
        )
        result = lookup_postcode("INVALID")
        assert result == {}


class TestLookupOutcode:
    """Tests for lookup_outcode."""

    @responses_lib.activate
    def test_happy_path(self):
        """Returns the result dict on a successful postcodes.io response."""
        responses_lib.add(
            responses_lib.GET,
            f"{POSTCODES_URL}/outcodes/SW1A",
            json={"status": 200, "result": OUTCODE_RESULT},
            status=200,
        )
        result = lookup_outcode("SW1A")
        assert result["outcode"] == "SW1A"
        assert result["latitude"] == 51.5028

    @responses_lib.activate
    def test_non_200_returns_empty(self):
        """Returns empty dict when the API responds with a non-200 status."""
        responses_lib.add(
            responses_lib.GET,
            f"{POSTCODES_URL}/outcodes/ZZZZZ",
            json={"status": 404, "error": "Outcode not found"},
            status=404,
        )
        result = lookup_outcode("ZZZZZ")
        assert result == {}
