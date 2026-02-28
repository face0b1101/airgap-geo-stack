"""Environment-variable configuration for airgap_geo services."""

from decouple import config

PHOTON_API: str = config("PHOTON_API", default="http://localhost:2322")
NOMINATIM_URL: str = config("NOMINATIM_URL", default="http://localhost:8080")
OSRM_API: str = config("OSRM_API", default="http://localhost:80")
POSTCODES_URL: str = config("POSTCODES_URL", default="http://localhost:8000")

# API server
API_PORT: int = config("API_PORT", default=5000, cast=int)

# Cache
CACHE_TTL_SECONDS: int = config("CACHE_TTL_SECONDS", default=3600, cast=int)
CACHE_MAX_SIZE: int = config("CACHE_MAX_SIZE", default=1024, cast=int)
