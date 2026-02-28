"""Shared fixtures for the API test suite."""

from __future__ import annotations

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

from airgap_geo_api.app import create_app
from airgap_geo_api.cache import (
    _geocode_cache,
    _postcode_cache,
    _route_cache,
)


@pytest.fixture(autouse=True)
def clear_caches():
    """Clear all in-process caches before each test to prevent cross-test pollution."""
    _geocode_cache.clear()
    _route_cache.clear()
    _postcode_cache.clear()
    yield
    _geocode_cache.clear()
    _route_cache.clear()
    _postcode_cache.clear()


@pytest.fixture()
def client(httpx_mock) -> Generator[TestClient]:
    """Return a TestClient wrapping a fresh app instance with lifespan active."""
    with TestClient(create_app()) as tc:
        yield tc
