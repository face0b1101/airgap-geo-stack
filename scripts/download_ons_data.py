#!/usr/bin/env python3
"""Download ONS Open Geography register CSVs, boundary GeoJSON, and ONSPD.

Uses the ArcGIS REST API hosted at services1.arcgis.com/ESMARspQHYMw9BZ9.
Handles pagination automatically for large datasets.

Usage:
    python scripts/download_ons_data.py [--registers] [--boundaries] [--onspd] [--all]
"""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
import time
from pathlib import Path

BASE_URL = "https://services1.arcgis.com/ESMARspQHYMw9BZ9/arcgis/rest/services"
DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "ons"
PAGE_SIZE = 2000

REGISTERS: dict[str, dict] = {
    "LAD_DEC_2024_UK": {
        "service": "LAD_DEC_2024_UK_NC",
        "description": "Local Authority Districts",
    },
    "WD_DEC_2024_UK": {
        "service": "WD_DEC_2024_UK_NC",
        "description": "Wards",
    },
    "LSOA_DEC_2021_EW": {
        "service": "LSOA_DEC_2021_EW_NC_v3",
        "description": "Lower Layer Super Output Areas (2021)",
    },
    "MSOA_DEC_2021_EW": {
        "service": "MSOA_DEC_2021_EW_NC_v3",
        "description": "Middle Layer Super Output Areas (2021)",
    },
    "PCON_2024_UK": {
        "service": "PCON_2024_UK_NC_v2",
        "description": "Parliamentary Constituencies (2024)",
    },
    "PAR_DEC_2024_EW": {
        "service": "PAR_DEC_2024_EW_NC",
        "description": "Parishes",
    },
    "ICB_DEC_2024_EN": {
        "service": "ICB_DEC_2024_EN_NC",
        "description": "Integrated Care Boards",
    },
    "SICBL_DEC_2024_EN": {
        "service": "SICBL_DEC_2024_EN_NC",
        "description": "Sub-ICB Locations",
    },
    "PFA_DEC_2024_UK": {
        "service": "PFA_DEC_2024_UK_NC",
        "description": "Police Force Areas",
    },
    "RGN_DEC_2024_EN": {
        "service": "RGN_DEC_2024_EN_NC",
        "description": "Regions",
    },
    "CTY_DEC_2024_EN": {
        "service": "CTY_DEC_2024_EN_NC",
        "description": "Counties",
    },
    "CTYUA_DEC_2024_UK": {
        "service": "CTYUA_DEC_2024_UK_NC",
        "description": "Counties and Unitary Authorities",
    },
    "NHSER_APR_2024_EN": {
        "service": "NHSER_APR_2024_EN_NC",
        "description": "NHS England Regions",
    },
    "NPARK_DEC_2024_GB": {
        "service": "NPARK_DEC_2024_GB_NC",
        "description": "National Parks",
    },
    "CAL_APR_2024_EN": {
        "service": "CAL_APR_2024_EN_NC",
        "description": "Cancer Alliances",
    },
    "CAUTH_MAY_2024_EN": {
        "service": "CAUTH_MAY_2024_EN_NC",
        "description": "Combined Authorities",
    },
    "CED_MAY_2024_EN": {
        "service": "CED_MAY_2024_EN_NC",
        "description": "County Electoral Divisions",
    },
    "LEP_APR_2023_EN": {
        "service": "LEP_APR_2023_NC_EN",
        "description": "Local Enterprise Partnerships",
    },
    "BUA_APR_2024_EW": {
        "service": "BUA_APR_2024_EW_NC",
        "description": "Built-up Areas",
    },
    "TTWA_2011_UK": {
        "service": "TTWA_2011_UK_NC_V4_664276d1d7604d4ea60a49debcdfcf64",
        "description": "Travel to Work Areas",
    },
    "ITL1_JAN_2025_UK": {
        "service": "ITL1_JAN_2025_UK_NC",
        "description": "International Territorial Level 1",
    },
    "ITL2_JAN_2025_UK": {
        "service": "ITL2_JAN_2025_UK_NC",
        "description": "International Territorial Level 2",
    },
    "ITL3_JAN_2025_UK": {
        "service": "ITL3_JAN_2025_UK_NC",
        "description": "International Territorial Level 3",
    },
    "MCTY_DEC_2024_EN": {
        "service": "MCTY_DEC_2024_EN_NC",
        "description": "Metropolitan Counties",
    },
}

# BGC = Generalised Clipped — good balance of detail vs file size
BOUNDARIES: dict[str, dict] = {
    "LAD_DEC_2024_UK_BGC": {
        "service": "Local_Authority_Districts_December_2024_Boundaries_UK_BGC",
        "description": "Local Authority Districts boundaries",
    },
    "WD_DEC_2024_UK_BGC": {
        "service": "Wards_December_2024_Boundaries_UK_BGC",
        "description": "Wards boundaries",
    },
    "LSOA_DEC_2021_EW_BGC": {
        "service": "Lower_layer_Super_Output_Areas_December_2021_Boundaries_EW_BGC_V5",
        "description": "LSOA boundaries (2021)",
    },
    "MSOA_DEC_2021_EW_BGC": {
        "service": "Middle_layer_Super_Output_Areas_December_2021_Boundaries_EW_BGC_V3",
        "description": "MSOA boundaries (2021)",
    },
    "PCON_JUL_2024_UK_BGC": {
        "service": "Westminster_Parliamentary_Constituencies_July_2024_Boundaries_UK_BGC",
        "description": "Parliamentary Constituency boundaries",
    },
    "RGN_DEC_2024_EN_BGC": {
        "service": "Regions_December_2024_Boundaries_EN_BGC",
        "description": "Regions boundaries",
    },
    "CTY_DEC_2024_EN_BGC": {
        "service": "Counties_December_2024_Boundaries_EN_BGC",
        "description": "Counties boundaries",
    },
    "PFA_DEC_2024_EW_BGC": {
        "service": "Police_Force_Areas_(December_2024)_Boundaries_EW_BGC",
        "description": "Police Force Areas boundaries",
    },
}

ONSPD_SERVICE = "ONSPD_NOV_2025_UK"


def _query_url(service: str, *, fmt: str = "json", offset: int = 0) -> str:
    return (
        f"{BASE_URL}/{service}/FeatureServer/0/query"
        f"?where=1%3D1&outFields=*&f={fmt}"
        f"&resultRecordCount={PAGE_SIZE}&resultOffset={offset}"
    )


def _count_url(service: str) -> str:
    return (
        f"{BASE_URL}/{service}/FeatureServer/0/query"
        f"?where=1%3D1&returnCountOnly=true&f=json"
    )


def _fetch_json(url: str, *, retries: int = 3) -> dict:
    for attempt in range(retries):
        try:
            result = subprocess.run(
                ["curl", "-sS", "--fail", "-L", "--max-time", "120", url],
                capture_output=True,
                check=True,
            )
            return json.loads(result.stdout)
        except (subprocess.CalledProcessError, json.JSONDecodeError) as exc:
            if attempt == retries - 1:
                raise RuntimeError(f"Failed after {retries} attempts: {exc}") from exc
            wait = 2 ** (attempt + 1)
            print(f"  Retry {attempt + 1}/{retries} after {wait}s: {exc}")
            time.sleep(wait)
    return {}  # unreachable


def get_record_count(service: str) -> int:
    """Return the total record count for an ONS ArcGIS feature service."""
    data = _fetch_json(_count_url(service))
    return data.get("count", 0)


def download_csv(service: str, dest: Path) -> int:
    """Download all records as CSV via paginated JSON queries."""
    count = get_record_count(service)
    print(f"  Records: {count}")

    all_rows: list[dict] = []
    offset = 0
    while offset < count:
        data = _fetch_json(_query_url(service, offset=offset))
        features = data.get("features", [])
        if not features:
            break
        for f in features:
            all_rows.append(f["attributes"])
        offset += len(features)
        if offset < count:
            print(f"  Fetched {offset}/{count}...")

    if not all_rows:
        print("  WARNING: No records returned")
        return 0

    fieldnames = list(all_rows[0].keys())
    with open(dest, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_rows)

    print(f"  Saved {len(all_rows)} records -> {dest.name}")
    return len(all_rows)


def download_geojson(service: str, dest: Path) -> int:
    """Download all records as GeoJSON via paginated queries."""
    count = get_record_count(service)
    print(f"  Records: {count}")

    all_features: list[dict] = []
    offset = 0
    while offset < count:
        data = _fetch_json(_query_url(service, fmt="geojson", offset=offset))
        features = data.get("features", [])
        if not features:
            break
        all_features.extend(features)
        offset += len(features)
        if offset < count:
            print(f"  Fetched {offset}/{count}...")

    if not all_features:
        print("  WARNING: No features returned")
        return 0

    geojson = {
        "type": "FeatureCollection",
        "features": all_features,
    }
    with open(dest, "w", encoding="utf-8") as fh:
        json.dump(geojson, fh)

    size_mb = dest.stat().st_size / (1024 * 1024)
    print(f"  Saved {len(all_features)} features ({size_mb:.1f} MB) -> {dest.name}")
    return len(all_features)


def run_registers() -> None:
    """Download all configured names-and-codes register CSVs."""
    dest_dir = DATA_DIR / "registers"
    dest_dir.mkdir(parents=True, exist_ok=True)
    for name, info in REGISTERS.items():
        dest = dest_dir / f"{name}.csv"
        if dest.exists():
            print(f"[SKIP] {info['description']} ({dest.name} already exists)")
            continue
        print(f"[DL] {info['description']} ({info['service']})")
        try:
            download_csv(info["service"], dest)
        except Exception as exc:
            print(f"  ERROR: {exc}")


def run_boundaries() -> None:
    """Download all configured boundary GeoJSON files."""
    dest_dir = DATA_DIR / "boundaries"
    dest_dir.mkdir(parents=True, exist_ok=True)
    for name, info in BOUNDARIES.items():
        dest = dest_dir / f"{name}.geojson"
        if dest.exists():
            print(f"[SKIP] {info['description']} ({dest.name} already exists)")
            continue
        print(f"[DL] {info['description']} ({info['service']})")
        try:
            download_geojson(info["service"], dest)
        except Exception as exc:
            print(f"  ERROR: {exc}")


def run_onspd() -> None:
    """Download the ONS Postcode Directory (ONSPD) CSV."""
    dest_dir = DATA_DIR / "onspd"
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / "ONSPD_NOV_2025_UK.csv"
    if dest.exists():
        print(f"[SKIP] ONSPD ({dest.name} already exists)")
        return
    print(f"[DL] ONSPD - ONS Postcode Directory November 2025 ({ONSPD_SERVICE})")
    try:
        download_csv(ONSPD_SERVICE, dest)
    except Exception as exc:
        print(f"  ERROR: {exc}")


def main() -> None:
    """CLI entry point for downloading ONS geography data."""
    parser = argparse.ArgumentParser(description="Download ONS geography data")
    parser.add_argument(
        "--registers", action="store_true", help="Download names & codes registers"
    )
    parser.add_argument(
        "--boundaries", action="store_true", help="Download boundary GeoJSON"
    )
    parser.add_argument(
        "--onspd", action="store_true", help="Download ONSPD postcode directory"
    )
    parser.add_argument("--all", action="store_true", help="Download everything")
    args = parser.parse_args()

    if not any([args.registers, args.boundaries, args.onspd, args.all]):
        args.all = True

    if args.registers or args.all:
        print("\n=== REGISTERS (Names & Codes CSVs) ===\n")
        run_registers()

    if args.boundaries or args.all:
        print("\n=== BOUNDARIES (GeoJSON) ===\n")
        run_boundaries()

    if args.onspd or args.all:
        print("\n=== ONSPD (Postcode Directory) ===\n")
        run_onspd()

    print("\nDone.")


if __name__ == "__main__":
    main()
