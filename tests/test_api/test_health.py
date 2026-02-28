"""Tests for GET /health."""

from __future__ import annotations

import re

import httpx
from fastapi.testclient import TestClient

from airgap_geo.settings import NOMINATIM_URL, OSRM_API, PHOTON_API, POSTCODES_URL

_OSRM_BASE = str(httpx.URL(OSRM_API))

_NOMINATIM_STATUS_URL = re.compile(rf"{re.escape(NOMINATIM_URL)}/status\.php.*")
_PHOTON_API_URL = re.compile(rf"{re.escape(PHOTON_API)}/api.*")
_OSRM_HEALTH_URL = re.compile(rf"{re.escape(_OSRM_BASE)}/route/v1/driving.*")
_POSTCODES_HEALTH_URL = re.compile(rf"{re.escape(POSTCODES_URL)}/postcodes/SW1A2AA.*")


class TestHealthEndpoint:
    """Tests for GET /health."""

    def test_all_services_up_returns_healthy(self, client: TestClient, httpx_mock):
        """Returns overall 'healthy' when all four backends respond 200."""
        httpx_mock.add_response(url=_NOMINATIM_STATUS_URL, status_code=200)
        httpx_mock.add_response(
            url=_PHOTON_API_URL, json={"features": []}, status_code=200
        )
        httpx_mock.add_response(
            url=_OSRM_HEALTH_URL, json={"code": "Ok", "routes": []}, status_code=200
        )
        httpx_mock.add_response(
            url=_POSTCODES_HEALTH_URL,
            json={"status": 200, "result": {}},
            status_code=200,
        )
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        for svc in ("nominatim", "photon", "osrm", "postcodes_io"):
            assert data["services"][svc]["status"] == "up"

    def test_all_services_down_returns_unhealthy(self, client: TestClient, httpx_mock):
        """Returns overall 'unhealthy' when all backends fail."""
        httpx_mock.add_response(url=_NOMINATIM_STATUS_URL, status_code=503)
        httpx_mock.add_response(url=_PHOTON_API_URL, status_code=503)
        httpx_mock.add_response(url=_OSRM_HEALTH_URL, status_code=503)
        httpx_mock.add_response(url=_POSTCODES_HEALTH_URL, status_code=503)
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "unhealthy"

    def test_partial_failure_returns_degraded(self, client: TestClient, httpx_mock):
        """Returns overall 'degraded' when some backends are up and some down."""
        httpx_mock.add_response(url=_NOMINATIM_STATUS_URL, status_code=200)
        httpx_mock.add_response(url=_PHOTON_API_URL, status_code=503)
        httpx_mock.add_response(url=_OSRM_HEALTH_URL, status_code=200)
        httpx_mock.add_response(url=_POSTCODES_HEALTH_URL, status_code=503)
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "degraded"
        assert data["services"]["nominatim"]["status"] == "up"
        assert data["services"]["photon"]["status"] == "down"

    def test_response_includes_latency(self, client: TestClient, httpx_mock):
        """Each service entry includes a latency_ms field when the probe succeeds."""
        httpx_mock.add_response(url=_NOMINATIM_STATUS_URL, status_code=200)
        httpx_mock.add_response(url=_PHOTON_API_URL, status_code=200)
        httpx_mock.add_response(url=_OSRM_HEALTH_URL, status_code=200)
        httpx_mock.add_response(url=_POSTCODES_HEALTH_URL, status_code=200)
        response = client.get("/health")
        data = response.json()
        for svc in data["services"].values():
            assert svc["latency_ms"] is not None
            assert svc["latency_ms"] >= 0
