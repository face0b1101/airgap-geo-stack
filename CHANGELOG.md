# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-02-27

### Added

- Initial project created from python-uv-boilerplate template
- `airgap_geocoding` Python library with `geocoder`, `route`, `lookup_postcode`, and `lookup_outcode` public API
- Docker Compose stacks for Nominatim, Photon, OSRM (driving/walking/cycling), HAProxy, and postcodes.io
- Air-gap deployment guide in `docker/README.md`
- pytest test suite using `responses` to mock all HTTP calls

[Unreleased]: https://github.com/face0b1101/airgap-geocoding-stack/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/face0b1101/airgap-geocoding-stack/releases/tag/v0.1.0
