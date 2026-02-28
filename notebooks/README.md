# Air-Gap Geo Stack — Demonstration Notebooks

A collection of interactive notebooks demonstrating the `airgap_geo` Python library
running against the self-hosted Docker services. All HTTP traffic stays on localhost —
no external APIs are called.

Each notebook is **fully self-contained** with its own service startup, health checks,
imports, and teardown cells.

______________________________________________________________________

## Notebooks

| Notebook                                                 | Services used           | Description                                                                                             |
| -------------------------------------------------------- | ----------------------- | ------------------------------------------------------------------------------------------------------- |
| [01-geocoding.ipynb](01-geocoding.ipynb)                 | Nominatim, Photon       | Forward geocoding (place name → coordinates) and reverse geocoding (coordinates → address)              |
| [02-routing.ipynb](02-routing.ipynb)                     | OSRM, Nominatim, Photon | Basic A-to-B routing across driving, walking, and cycling profiles                                      |
| [03-routing-enhanced.ipynb](03-routing-enhanced.ipynb)   | OSRM, Nominatim, Photon | Advanced routing: waypoints, turn-by-turn steps, alternative routes, annotations, road-class exclusions |
| [04-postcodes.ipynb](04-postcodes.ipynb)                 | postcodes.io            | UK full postcode and outcode (district) lookup                                                          |
| [05-combined-workflow.ipynb](05-combined-workflow.ipynb) | All four                | End-to-end scenario: postcodes → geocoding → routing → map                                              |
| [06-fastapi.ipynb](06-fastapi.ipynb)                     | All four + API          | REST API walkthrough: all endpoints via HTTP requests                                                   |
| [07-performance.ipynb](07-performance.ipynb)             | All four + API          | Performance comparison: library vs FastAPI (latency, caching, concurrency)                              |

______________________________________________________________________

## Services Overview

| Service        | Default port | Docker Compose path |
| -------------- | ------------ | ------------------- |
| Nominatim      | 8080         | `docker/nominatim/` |
| Photon         | 2322         | `docker/photon/`    |
| OSRM + HAProxy | 80           | `docker/osrm/`      |
| postcodes.io   | 8000         | `docker/osrm/`      |
| FastAPI (API)  | 5000         | `docker/api/`       |

See the main [README.md](../README.md) for data preparation and deployment instructions.

Endpoint URLs are controlled by environment variables in `.env` (see `.env.example`).
