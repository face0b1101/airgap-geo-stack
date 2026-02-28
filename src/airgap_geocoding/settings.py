"""Environment-variable configuration for airgap_geocoding services."""

from decouple import config

PHOTON_API: str = config("PHOTON_API", default="http://localhost:2322")
NOMINATIM_URL: str = config("NOMINATIM_URL", default="http://localhost:8080")
OSRM_API: str = config("OSRM_API", default="http://localhost:80")
POSTCODES_URL: str = config("POSTCODES_URL", default="http://localhost:8000")
